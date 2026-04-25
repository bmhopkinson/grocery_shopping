import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Alert,
  CircularProgress,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import SaveIcon from '@mui/icons-material/Save'
import CancelIcon from '@mui/icons-material/Cancel'
import SortIcon from '@mui/icons-material/Sort'
import NotificationsIcon from '@mui/icons-material/Notifications'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'

export default function WorkingListDetail({ list, onBack }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const [addForm, setAddForm] = useState({ name: '', amount: '', unit: '', submitting: false })
  const [edit, setEdit] = useState({ id: null, name: '', amount: '', unit: '' })

  // Organize by store
  const [organizing, setOrganizing] = useState(false)

  // Dump to Reminders dialog
  const [dumpDialog, setDumpDialog] = useState({ open: false, submitting: false })
  const [reminderLists, setReminderLists] = useState([])
  const [selectedReminderList, setSelectedReminderList] = useState('')
  const [newReminderListName, setNewReminderListName] = useState('')

  // Organize existing Reminders list (accordion)
  const [reorderLists, setReorderLists] = useState([])
  const [reorderSelected, setReorderSelected] = useState('')
  const [reordering, setReordering] = useState(false)
  const [reorderResult, setReorderResult] = useState(null)

  const fetchItems = useCallback(async () => {
    try {
      const res = await fetch(`/api/working-lists/${list.id}/items`)
      if (!res.ok) throw new Error('Failed to load items')
      setItems(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [list.id])

  useEffect(() => { fetchItems() }, [fetchItems])

  // --- Item CRUD ---

  const handleAdd = async () => {
    if (!addForm.name.trim()) return
    setAddForm(f => ({ ...f, submitting: true }))
    try {
      const res = await fetch(`/api/working-lists/${list.id}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: addForm.name.trim(),
          amount: addForm.amount.trim(),
          unit: addForm.unit.trim(),
        }),
      })
      if (!res.ok) throw new Error('Failed to add item')
      const item = await res.json()
      setItems(prev => [...prev, item])
      setAddForm({ name: '', amount: '', unit: '', submitting: false })
    } catch (e) {
      setError(e.message)
      setAddForm(f => ({ ...f, submitting: false }))
    }
  }

  const handleSaveEdit = async () => {
    try {
      const res = await fetch(`/api/working-lists/${list.id}/items/${edit.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: edit.name.trim(), amount: edit.amount.trim(), unit: edit.unit.trim() }),
      })
      if (!res.ok) throw new Error('Failed to update item')
      const updated = await res.json()
      setItems(prev => prev.map(i => i.id === edit.id ? updated : i))
      setEdit({ id: null, name: '', amount: '', unit: '' })
    } catch (e) {
      setError(e.message)
    }
  }

  const handleDelete = async (itemId) => {
    try {
      const res = await fetch(`/api/working-lists/${list.id}/items/${itemId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete item')
      setItems(prev => prev.filter(i => i.id !== itemId))
    } catch (e) {
      setError(e.message)
    }
  }

  const handleClearAll = async () => {
    try {
      await fetch(`/api/working-lists/${list.id}/items`, { method: 'DELETE' })
      setItems([])
    } catch (e) {
      setError(e.message)
    }
  }

  // --- Organize by store ---

  const handleOrganize = async () => {
    setOrganizing(true)
    setError(null)
    try {
      const res = await fetch(`/api/working-lists/${list.id}/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: items.map(i => i.id) }),
      })
      if (!res.ok) throw new Error('Failed to organize list')
      const data = await res.json()
      setItems(data.reordered)
      setSuccess(`Organized ${data.count} items by store layout`)
    } catch (e) {
      setError(e.message)
    } finally {
      setOrganizing(false)
    }
  }

  // --- Dump to Reminders ---

  const openDumpDialog = async () => {
    let lists = []
    try {
      const res = await fetch('/api/reminder-lists')
      if (res.ok) lists = (await res.json()).lists || []
    } catch { /* empty */ }
    setReminderLists(lists)
    setSelectedReminderList(lists[0] || '')
    setNewReminderListName('')
    setDumpDialog({ open: true, submitting: false })
  }

  const handleDump = async () => {
    const targetList = newReminderListName.trim() || selectedReminderList
    if (!targetList) return
    setDumpDialog(d => ({ ...d, submitting: true }))
    try {
      const res = await fetch(`/api/working-lists/${list.id}/dump-to-reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ list_name: targetList }),
      })
      if (!res.ok) throw new Error('Failed to send to Reminders')
      const data = await res.json()
      setDumpDialog({ open: false, submitting: false })
      setSuccess(`Sent ${data.added} item${data.added !== 1 ? 's' : ''} to "${data.list_name}"`)
    } catch (e) {
      setError(e.message)
      setDumpDialog(d => ({ ...d, submitting: false }))
    }
  }

  // --- Organize existing Reminders list ---

  useEffect(() => {
    fetch('/api/reminder-lists')
      .then(r => r.ok ? r.json() : { lists: [] })
      .then(d => {
        setReorderLists(d.lists || [])
        if (d.lists?.length) setReorderSelected(d.lists[0])
      })
      .catch(() => {})
  }, [])

  const handleReorderReminders = async () => {
    if (!reorderSelected) return
    setReordering(true)
    setReorderResult(null)
    try {
      const res = await fetch('/api/reorder-reminders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ list_name: reorderSelected }),
      })
      if (!res.ok) throw new Error('Failed to organize Reminders list')
      setReorderResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setReordering(false)
    }
  }

  // ---

  const formatItemLabel = (item) => {
    const parts = [item.amount, item.unit].filter(Boolean).join(' ')
    return parts ? `${item.name} — ${parts}` : item.name
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={onBack} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h5">{list.name}</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {/* Action buttons */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Button
          variant="outlined"
          startIcon={organizing ? <CircularProgress size={16} /> : <SortIcon />}
          onClick={handleOrganize}
          disabled={organizing || items.length === 0}
        >
          Organize by Store
        </Button>
        <Button
          variant="contained"
          startIcon={<NotificationsIcon />}
          onClick={openDumpDialog}
          disabled={items.length === 0}
        >
          Send to Reminders
        </Button>
        {items.length > 0 && (
          <Button variant="outlined" color="error" size="small" onClick={handleClearAll} sx={{ ml: 'auto' }}>
            Clear All
          </Button>
        )}
      </Box>

      {/* Add item form */}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>Add Item</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <TextField
            size="small"
            label="Item"
            value={addForm.name}
            onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            sx={{ flex: 3, minWidth: 140 }}
          />
          <TextField
            size="small"
            label="Amount"
            value={addForm.amount}
            onChange={e => setAddForm(f => ({ ...f, amount: e.target.value }))}
            sx={{ flex: 1, minWidth: 80 }}
          />
          <TextField
            size="small"
            label="Unit"
            value={addForm.unit}
            onChange={e => setAddForm(f => ({ ...f, unit: e.target.value }))}
            sx={{ flex: 1, minWidth: 80 }}
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAdd}
            disabled={!addForm.name.trim() || addForm.submitting}
            sx={{ height: 40 }}
          >
            Add
          </Button>
        </Box>
      </Paper>

      {/* Item list */}
      {items.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No items yet. Add some above or plan a meal to populate this list.
        </Typography>
      ) : (
        <Paper variant="outlined">
          <List dense disablePadding>
            {items.map((item, idx) => (
              <Box key={item.id}>
                {idx > 0 && <Divider />}
                <ListItem
                  secondaryAction={
                    edit.id !== item.id ? (
                      <Box>
                        <IconButton size="small" onClick={() => setEdit({ id: item.id, name: item.name, amount: item.amount, unit: item.unit })}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleDelete(item.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ) : null
                  }
                >
                  {edit.id === item.id ? (
                    <Box sx={{ display: 'flex', gap: 1, flex: 1, flexWrap: 'wrap', alignItems: 'center', pr: 1 }}>
                      <TextField size="small" label="Item" value={edit.name} onChange={e => setEdit(s => ({ ...s, name: e.target.value }))} sx={{ flex: 3 }} />
                      <TextField size="small" label="Amount" value={edit.amount} onChange={e => setEdit(s => ({ ...s, amount: e.target.value }))} sx={{ flex: 1, minWidth: 70 }} />
                      <TextField size="small" label="Unit" value={edit.unit} onChange={e => setEdit(s => ({ ...s, unit: e.target.value }))} sx={{ flex: 1, minWidth: 70 }} />
                      <IconButton size="small" color="primary" onClick={handleSaveEdit}><SaveIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => setEdit({ id: null, name: '', amount: '', unit: '' })}><CancelIcon fontSize="small" /></IconButton>
                    </Box>
                  ) : (
                    <ListItemText primary={formatItemLabel(item)} />
                  )}
                </ListItem>
              </Box>
            ))}
          </List>
        </Paper>
      )}

      {/* Organize an existing Reminders list */}
      <Accordion sx={{ mt: 3 }} disableGutters>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Organize an Existing Reminders List</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Reorder an Apple Reminders list by store layout: produce → meat → dairy → frozen → etc.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Reminders List</InputLabel>
              <Select
                value={reorderSelected}
                label="Reminders List"
                onChange={e => { setReorderSelected(e.target.value); setReorderResult(null) }}
                disabled={reordering}
              >
                {reorderLists.map(l => <MenuItem key={l} value={l}>{l}</MenuItem>)}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              startIcon={reordering ? <CircularProgress size={16} /> : <SortIcon />}
              onClick={handleReorderReminders}
              disabled={!reorderSelected || reordering}
            >
              Organize
            </Button>
          </Box>
          {reorderResult && (
            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <CheckCircleOutlineIcon color="success" fontSize="small" />
              <Typography variant="body2" color="success.main">
                Reordered {reorderResult.count} items in &ldquo;{reorderResult.list_name}&rdquo;
              </Typography>
            </Box>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Dump to Reminders dialog */}
      <Dialog open={dumpDialog.open} onClose={() => setDumpDialog({ open: false, submitting: false })} maxWidth="xs" fullWidth>
        <DialogTitle>Send to Reminders</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {items.length} item{items.length !== 1 ? 's' : ''} will be added (existing items with matching names will have quantities merged).
          </Typography>

          {reminderLists.length > 0 && (
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Select existing list</InputLabel>
              <Select
                value={selectedReminderList}
                label="Select existing list"
                onChange={e => { setSelectedReminderList(e.target.value); setNewReminderListName('') }}
              >
                {reminderLists.map(l => <MenuItem key={l} value={l}>{l}</MenuItem>)}
              </Select>
            </FormControl>
          )}

          <TextField
            fullWidth
            size="small"
            label="Or create new list"
            placeholder="e.g., Groceries"
            value={newReminderListName}
            onChange={e => { setNewReminderListName(e.target.value); setSelectedReminderList('') }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDumpDialog({ open: false, submitting: false })}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleDump}
            disabled={(!selectedReminderList && !newReminderListName.trim()) || dumpDialog.submitting}
          >
            {dumpDialog.submitting ? 'Sending…' : 'Send to Reminders'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
