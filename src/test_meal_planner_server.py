#!/usr/bin/env python3
"""
Test script for the Meal Planner SSE Server.

Usage:
    # First, start the server in another terminal:
    uvicorn meal_planner_server:app --host 0.0.0.0 --port 8000

    # Then run this script:
    python test_meal_planner_server.py

    # Or run specific tests:
    python test_meal_planner_server.py --health      # Just health check
    python test_meal_planner_server.py --full        # Full interactive flow
"""

import argparse
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"


def print_event(event_type: str, data: dict):
    """Pretty print an SSE event."""
    print(f"\n{'='*60}")
    print(f"EVENT: {event_type}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2))


def stream_sse(response: httpx.Response):
    """Parse SSE events from a streaming response."""
    event_type = None
    data_lines = []

    for line in response.iter_lines():
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line == "":
            # Empty line signals end of event
            if event_type and data_lines:
                data = json.loads("".join(data_lines))
                yield event_type, data
            event_type = None
            data_lines = []


def test_health():
    """Test the health check endpoint."""
    print("\n--- Testing Health Endpoint ---")
    with httpx.Client() as client:
        resp = client.get(f"{BASE_URL}/health")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        return resp.status_code == 200


def test_start_plan(cuisine_type: str = "italian") -> str | None:
    """
    Start a new planning session and stream events until an interrupt.
    Returns the session_id.
    """
    print(f"\n--- Starting Plan (cuisine: {cuisine_type}) ---")

    session_id = None

    with httpx.Client(timeout=120.0) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/plan",
            json={"cuisine_type": cuisine_type},
            headers={"Accept": "text/event-stream"}
        ) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return None

            for event_type, data in stream_sse(response):
                print_event(event_type, data)

                if event_type == "session_start":
                    session_id = data["session_id"]
                    print(f"\n>>> Session ID: {session_id}")

                if event_type in ("meal_options", "ingredient_review", "reminders_prompt"):
                    print(f"\n>>> Interrupt reached: {event_type}")
                    print(">>> Stopping stream for user input")
                    break

                if event_type == "complete":
                    print("\n>>> Flow completed!")
                    break

                if event_type == "error":
                    print(f"\n>>> Error: {data['message']}")
                    break

    return session_id


def test_resume_session(session_id: str, user_input: str):
    """Resume a session with user input."""
    print(f"\n--- Resuming Session {session_id} ---")
    print(f"User input: {user_input}")

    with httpx.Client(timeout=120.0) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/sessions/{session_id}/resume",
            json={"input": user_input},
            headers={"Accept": "text/event-stream"}
        ) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return False

            for event_type, data in stream_sse(response):
                print_event(event_type, data)

                if event_type in ("meal_options", "ingredient_review", "reminders_prompt"):
                    print(f"\n>>> Interrupt reached: {event_type}")
                    return event_type

                if event_type == "complete":
                    print("\n>>> Flow completed!")
                    return "complete"

                if event_type == "error":
                    print(f"\n>>> Error: {data['message']}")
                    return "error"

    return None


def test_get_session(session_id: str):
    """Get session state."""
    print(f"\n--- Getting Session State: {session_id} ---")
    with httpx.Client() as client:
        resp = client.get(f"{BASE_URL}/sessions/{session_id}")
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2))
        return resp.status_code == 200


def test_delete_session(session_id: str):
    """Delete a session."""
    print(f"\n--- Deleting Session: {session_id} ---")
    with httpx.Client() as client:
        resp = client.delete(f"{BASE_URL}/sessions/{session_id}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        return resp.status_code == 200


def run_interactive_flow():
    """Run the full interactive flow, prompting for user input at each interrupt."""
    print("\n" + "="*60)
    print("INTERACTIVE MEAL PLANNER TEST")
    print("="*60)

    cuisine = input("\nEnter cuisine type (default: italian): ").strip() or "italian"

    session_id = test_start_plan(cuisine)
    if not session_id:
        print("Failed to start session")
        return

    while True:
        # Check current state
        test_get_session(session_id)

        print("\n" + "-"*40)
        user_input = input("Enter your response (or 'quit' to exit): ").strip()

        if user_input.lower() == "quit":
            test_delete_session(session_id)
            break

        result = test_resume_session(session_id, user_input)

        if result == "complete":
            print("\n>>> Meal planning complete!")
            break
        elif result == "error":
            print("\n>>> An error occurred")
            break


def run_automated_test():
    """Run an automated test with preset responses."""
    print("\n" + "="*60)
    print("AUTOMATED MEAL PLANNER TEST")
    print("="*60)

    # Start with Italian cuisine
    session_id = test_start_plan("italian")
    if not session_id:
        print("Failed to start session")
        return False

    # Simulate selecting meal option 1
    print("\n>>> Auto-selecting first meal option...")
    result = test_resume_session(session_id, "1")

    if result == "ingredient_review":
        # Approve ingredients
        print("\n>>> Auto-approving ingredients...")
        result = test_resume_session(session_id, "yes")

    if result == "reminders_prompt":
        # Skip reminders
        print("\n>>> Skipping reminders...")
        result = test_resume_session(session_id, "skip")

    if result == "complete":
        print("\n>>> Test completed successfully!")
        return True
    else:
        print(f"\n>>> Test ended with: {result}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test the Meal Planner SSE Server")
    parser.add_argument("--health", action="store_true", help="Run health check only")
    parser.add_argument("--full", action="store_true", help="Run interactive flow")
    parser.add_argument("--auto", action="store_true", help="Run automated test with preset responses")
    parser.add_argument("--start", type=str, metavar="CUISINE", help="Start a plan with given cuisine and stop at first interrupt")
    parser.add_argument("--resume", nargs=2, metavar=("SESSION_ID", "INPUT"), help="Resume a session with input")
    parser.add_argument("--state", type=str, metavar="SESSION_ID", help="Get session state")
    parser.add_argument("--delete", type=str, metavar="SESSION_ID", help="Delete a session")

    args = parser.parse_args()

    # If no arguments, run health check and start a basic test
    if len(sys.argv) == 1:
        print("Running basic test (use --help for more options)")
        if test_health():
            print("\nHealth check passed!")
            test_start_plan("italian")
        else:
            print("\nHealth check failed - is the server running?")
            print("Start it with: uvicorn meal_planner_server:app --port 8000")
        return

    if args.health:
        test_health()
    elif args.full:
        run_interactive_flow()
    elif args.auto:
        run_automated_test()
    elif args.start:
        test_start_plan(args.start)
    elif args.resume:
        test_resume_session(args.resume[0], args.resume[1])
    elif args.state:
        test_get_session(args.state)
    elif args.delete:
        test_delete_session(args.delete)


if __name__ == "__main__":
    main()
