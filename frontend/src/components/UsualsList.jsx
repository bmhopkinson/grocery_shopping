import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Checkbox,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Paper,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import NotificationsIcon from '@mui/icons-material/Notifications'
import SaveIcon from '@mui/icons-material/Save'
import CancelIcon from '@mui/icons-material/Cancel'

const CATEGORIES = ['Breakfast', 'Lunch', ,'Snacks', 'Other']

export default function UsualsList() {
  const [usuals, setUsuals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Add form
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [adding, setAdding] = useState(false)

  // Edit state
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editCategory, setEditCategory] = useState('')

  // Selection
  const [selected, setSelected] = useState(new Set())

  // Reminders dialog
  const [dialogOpen, setDialogOpen] = useState(false)
  const [reminderLists, setReminderLists] = useState([])
  const [selectedList, setSelectedList] = useState('')
  const [newListName, setNewListName] = useState('')
  const [addingToReminders, setAddingToReminders] = useState(false)

  const fetchUsuals = useCallback(async () => {
    try {
      const res = await fetch('/api/usuals')
      if (!res.ok) throw new Error('Failed to load usuals')
      setUsuals(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchUsuals() }, [fetchUsuals])

  const handleAdd = async () => {
    if (!newName.trim()) return
    setAdding(true)
    try {
      const res = await fetch('/api/usuals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), category: newCategory || null }),
      })
      if (!res.ok) throw new Error('Failed to add item')
      const item = await res.json()
      setUsuals(prev => [...prev, item])
      setNewName('')
      setNewCategory('')
    } catch (e) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  const handleEdit = (item) => {
    setEditingId(item.id)
    setEditName(item.name)
    setEditCategory(item.category || '')
  }

  const handleSaveEdit = async () => {
    try {
      const res = await fetch(`/api/usuals/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName.trim(), category: editCategory || null }),
      })
      if (!res.ok) throw new Error('Failed to update item')
      const updated = await res.json()
      setUsuals(prev => prev.map(u => u.id === editingId ? updated : u))
      setEditingId(null)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`/api/usuals/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete item')
      setUsuals(prev => prev.filter(u => u.id !== id))
      setSelected(prev => { const s = new Set(prev); s.delete(id); return s })
    } catch (e) {
      setError(e.message)
    }
  }

  const toggleSelect = (id) => {
    setSelected(prev => {
      const s = new Set(prev)
      s.has(id) ? s.delete(id) : s.add(id)
      return s
    })
  }

  const openRemindersDialog = async () => {
    try {
      const res = await fetch('/api/reminder-lists')
      if (res.ok) {
        const data = await res.json()
        setReminderLists(data.lists || [])
      }
    } catch {
      setReminderLists([])
    }
    setSelectedList('')
    setNewListName('')
    setDialogOpen(true)
  }

  const handleAddToReminders = async () => {
    const listName = newListName.trim() || selectedList
    if (!listName) return
    setAddingToReminders(true)
    try {
      const res = await fetch('/api/usuals/add-to-reminders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usual_ids: Array.from(selected), list_name: listName }),
      })
      if (!res.ok) throw new Error('Failed to add to Reminders')
      const data = await res.json()
      setDialogOpen(false)
      setSelected(new Set())
      setSuccess(`Added ${data.added.length} item${data.added.length !== 1 ? 's' : ''} to "${data.list_name}"`)
    } catch (e) {
      setError(e.message)
    } finally {
      setAddingToReminders(false)
    }
  }

  // Group usuals by category
  const grouped = usuals.reduce((acc, item) => {
    const cat = item.category || 'Uncategorized'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(item)
    return acc
  }, {})

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Restock Usuals</Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Add new item */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>Add Item</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <TextField
            size="small"
            label="Item name"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            sx={{ flex: 2, minWidth: 150 }}
          />
          <FormControl size="small" sx={{ flex: 1, minWidth: 130 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={newCategory}
              label="Category"
              onChange={e => setNewCategory(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {CATEGORIES.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAdd}
            disabled={!newName.trim() || adding}
            sx={{ height: 40 }}
          >
            Add
          </Button>
        </Box>
      </Paper>

      {/* Selection bar */}
      {usuals.length > 0 && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {selected.size} of {usuals.length} selected
          </Typography>
          <Button size="small" onClick={() => setSelected(new Set(usuals.map(u => u.id)))}>
            All
          </Button>
          <Button size="small" onClick={() => setSelected(new Set())}>
            None
          </Button>
          <Box sx={{ flex: 1 }} />
          <Button
            variant="contained"
            color="secondary"
            startIcon={<NotificationsIcon />}
            disabled={selected.size === 0}
            onClick={openRemindersDialog}
          >
            Add {selected.size > 0 ? selected.size : ''} to Reminders
          </Button>
        </Box>
      )}

      {/* Items grouped by category */}
      {usuals.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 6 }}>
          No items yet. Add your regular grocery items above.
        </Typography>
      ) : (
        Object.entries(grouped).map(([category, items]) => (
          <Accordion key={category} defaultExpanded disableGutters elevation={1} sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="medium">
                {category}
              </Typography>
              <Chip label={items.length} size="small" sx={{ ml: 1 }} />
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <List dense disablePadding>
                {items.map((item, idx) => (
                  <Box key={item.id}>
                    {idx > 0 && <Divider />}
                    <ListItem
                      secondaryAction={
                        editingId !== item.id ? (
                          <Box>
                            <IconButton size="small" onClick={() => handleEdit(item)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" onClick={() => handleDelete(item.id)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        ) : null
                      }
                    >
                      <Checkbox
                        checked={selected.has(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        size="small"
                        sx={{ mr: 1 }}
                      />
                      {editingId === item.id ? (
                        <Box sx={{ display: 'flex', gap: 1, flex: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                          <TextField
                            size="small"
                            value={editName}
                            onChange={e => setEditName(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSaveEdit()}
                            sx={{ flex: 2 }}
                          />
                          <FormControl size="small" sx={{ flex: 1, minWidth: 110 }}>
                            <InputLabel>Category</InputLabel>
                            <Select
                              value={editCategory}
                              label="Category"
                              onChange={e => setEditCategory(e.target.value)}
                            >
                              <MenuItem value="">None</MenuItem>
                              {CATEGORIES.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                            </Select>
                          </FormControl>
                          <IconButton size="small" color="primary" onClick={handleSaveEdit}>
                            <SaveIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => setEditingId(null)}>
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      ) : (
                        <ListItemText primary={item.name} />
                      )}
                    </ListItem>
                  </Box>
                ))}
              </List>
            </AccordionDetails>
          </Accordion>
        ))
      )}

      {/* Add to Reminders dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add to Reminders</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Adding {selected.size} item{selected.size !== 1 ? 's' : ''} to a Reminders list.
          </Typography>
          {reminderLists.length > 0 && (
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Select existing list</InputLabel>
              <Select
                value={selectedList}
                label="Select existing list"
                onChange={e => { setSelectedList(e.target.value); setNewListName('') }}
              >
                {reminderLists.map(l => <MenuItem key={l} value={l}>{l}</MenuItem>)}
              </Select>
            </FormControl>
          )}
          <TextField
            fullWidth
            label={reminderLists.length > 0 ? 'Or create new list' : 'List name'}
            value={newListName}
            onChange={e => { setNewListName(e.target.value); setSelectedList('') }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddToReminders}
            disabled={(!selectedList && !newListName.trim()) || addingToReminders}
          >
            {addingToReminders ? 'Adding…' : 'Add to Reminders'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
