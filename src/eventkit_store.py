"""
EventKit-based Apple Reminders integration (macOS only).

Wraps EKEventStore with synchronous helpers by converting EventKit's async
completion-handler APIs into blocking calls via threading.Event.

This module is imported by reminders_server.py and reminders.py. It must
never be imported inside Docker (reminders.py guards this with _use_proxy()).
"""

import sys

if sys.platform != "darwin":
    raise ImportError("eventkit_store is macOS-only and cannot be used inside Docker")

import logging
import threading

import EventKit

logger = logging.getLogger("reminders_proxy")

# EventKit entity type constant
_EK_ENTITY_REMINDER = EventKit.EKEntityTypeReminder

# EKSource type for iCloud/CalDAV — preferred when creating new lists
_EK_SOURCE_CALDAV = 5


class EventKitStore:
    """
    Synchronous wrapper around EKEventStore.

    All public methods return a (success: bool, value_or_error) tuple so
    callers can use the same pattern as the old run_applescript() helper.
    """

    def __init__(self, access_timeout: float = 15.0):
        self._store = EventKit.EKEventStore.alloc().init()
        self._access_timeout = access_timeout
        self._authorized = False

    # ------------------------------------------------------------------
    # Access request
    # ------------------------------------------------------------------

    def request_access(self) -> tuple[bool, str]:
        """
        Request Reminders access from the TCC daemon.

        Blocks until the user responds to the permission dialog (or times out).
        The grant persists for the lifetime of the process — this only needs
        to be called once at startup.
        """
        event = threading.Event()
        result: dict = {}

        def handler(granted, error):
            result["granted"] = bool(granted)
            result["error"] = str(error) if error else None
            event.set()

        self._store.requestAccessToEntityType_completion_(_EK_ENTITY_REMINDER, handler)
        signalled = event.wait(timeout=self._access_timeout)

        if not signalled:
            msg = f"TCC access request timed out after {self._access_timeout}s"
            logger.error(msg)
            return False, msg

        if result.get("granted"):
            self._authorized = True
            return True, "access granted"

        msg = result.get("error") or "access denied by user or TCC"
        logger.error("EventKit access denied: %s", msg)
        return False, msg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calendars(self):
        """Return all EKCalendar objects for Reminders."""
        return self._store.calendarsForEntityType_(_EK_ENTITY_REMINDER) or []

    def _get_calendar(self, list_name: str):
        """Return the EKCalendar with the given title, or None."""
        for cal in self._calendars():
            if cal.title() == list_name:
                return cal
        return None

    def _fetch_reminders(self, calendar, include_completed: bool = False) -> list:
        """
        Synchronously fetch reminders from a single calendar.

        EventKit's fetch API is async; we block using threading.Event.
        EventKit always calls the completion handler, so no timeout is needed.
        """
        predicate = self._store.predicateForRemindersInCalendars_([calendar])
        event = threading.Event()
        holder: dict = {}

        def handler(reminders):
            holder["reminders"] = list(reminders) if reminders else []
            event.set()

        self._store.fetchRemindersMatchingPredicate_completion_(predicate, handler)
        event.wait()

        reminders = holder["reminders"]
        if include_completed:
            return reminders
        return [r for r in reminders if not r.isCompleted()]

    def _best_source(self):
        """
        Return the best EKSource for creating a new reminder list.
        Prefers iCloud (CalDAV, sourceType==5), then falls back to local.
        """
        sources = self._store.sources() or []
        for src in sources:
            if src.sourceType() == _EK_SOURCE_CALDAV:
                return src
        for src in sources:
            if src.sourceType() == EventKit.EKSourceTypeLocal:
                return src
        return sources[0] if sources else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_default_list_name(self) -> tuple[bool, str]:
        """Return (True, name) for the default Reminders list."""
        try:
            cal = self._store.defaultCalendarForNewReminders()
            if cal is None:
                return False, "no default reminder list found"
            return True, cal.title()
        except Exception as e:
            return False, str(e)

    def get_all_lists(self) -> tuple[bool, list[str]]:
        """Return (True, [list_name, ...]) for every Reminders list."""
        try:
            names = [cal.title() for cal in self._calendars()]
            return True, names
        except Exception as e:
            return False, str(e)

    def list_exists(self, list_name: str) -> tuple[bool, bool]:
        """Return (True, exists_bool) — second value is whether the list exists."""
        try:
            return True, self._get_calendar(list_name) is not None
        except Exception as e:
            return False, str(e)

    def create_list(self, list_name: str) -> tuple[bool, str]:
        """Create a new Reminders list. Returns (True, '') or (False, error)."""
        try:
            cal = EventKit.EKCalendar.calendarForEntityType_eventStore_(
                _EK_ENTITY_REMINDER, self._store
            )
            cal.setTitle_(list_name)
            source = self._best_source()
            if source:
                cal.setSource_(source)
            ok = self._store.saveCalendar_commit_error_(cal, True, None)
            if not ok:
                return False, "unknown error saving calendar (check system logs)"
            return True, ""
        except Exception as e:
            return False, str(e)

    def create_reminder(self, list_name: str, text: str) -> tuple[bool, str]:
        """Add a reminder to the named list. Returns (True, '') or (False, error)."""
        try:
            cal = self._get_calendar(list_name)
            if cal is None:
                return False, f"list '{list_name}' not found"
            reminder = EventKit.EKReminder.reminderWithEventStore_(self._store)
            reminder.setTitle_(text)
            reminder.setCalendar_(cal)
            ok = self._store.saveReminder_commit_error_(reminder, True, None)
            if not ok:
                return False, "unknown error saving reminder (check system logs)"
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_list_items(self, list_name: str) -> tuple[bool, list[str]]:
        """Return (True, [title, ...]) for all incomplete reminders in a list."""
        try:
            cal = self._get_calendar(list_name)
            if cal is None:
                return False, f"list '{list_name}' not found"
            reminders = self._fetch_reminders(cal, include_completed=False)
            return True, [r.title() for r in reminders]
        except Exception as e:
            return False, str(e)

    def delete_reminder(self, list_name: str, text: str) -> tuple[bool, str]:
        """Delete all incomplete reminders with an exact title match."""
        try:
            cal = self._get_calendar(list_name)
            if cal is None:
                return False, f"list '{list_name}' not found"
            reminders = self._fetch_reminders(cal, include_completed=False)
            for r in reminders:
                if r.title() == text:
                    self._store.removeReminder_commit_error_(r, True, None)
            return True, ""
        except Exception as e:
            return False, str(e)

    def delete_reminders_batch(
        self, list_name: str, texts: list[str]
    ) -> tuple[bool, str]:
        """
        Delete multiple reminders by title in a single batched commit.

        Matches on incomplete reminders only (consistent with the old AppleScript
        batch delete which filtered `completed is false`).
        """
        try:
            cal = self._get_calendar(list_name)
            if cal is None:
                return False, f"list '{list_name}' not found"
            reminders = self._fetch_reminders(cal, include_completed=False)
            names_set = set(texts)
            targets = [r for r in reminders if r.title() in names_set]
            for r in targets:
                self._store.removeReminder_commit_error_(r, False, None)
            if targets:
                self._store.commit_(None)
            return True, ""
        except Exception as e:
            return False, str(e)


# Module-level singleton — imported by reminders_server.py and reminders.py
_store = EventKitStore()
