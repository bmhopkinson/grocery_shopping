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
import AddToWorkingListDialog from './AddToWorkingListDialog'

const CATEGORIES = ['Breakfast', 'Lunch', 'Snacks', 'Other']

export default function UsualsList() {
  const [usuals, setUsuals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [selected, setSelected] = useState(new Set())

  const [addForm, setAddForm] = useState({ name: '', category: '', submitting: false })
  const [edit, setEdit] = useState({ id: null, name: '', category: '' })
  const [dialog, setDialog] = useState({ open: false, lists: [], submitting: false })

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
    if (!addForm.name.trim()) return
    setAddForm(f => ({ ...f, submitting: true }))
    try {
      const res = await fetch('/api/usuals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: addForm.name.trim(), category: addForm.category || null }),
      })
      if (!res.ok) throw new Error('Failed to add item')
      const item = await res.json()
      setUsuals(prev => [...prev, item])
      setAddForm({ name: '', category: '', submitting: false })
    } catch (e) {
      setError(e.message)
      setAddForm(f => ({ ...f, submitting: false }))
    }
  }

  const handleSaveEdit = async () => {
    try {
      const res = await fetch(`/api/usuals/${edit.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: edit.name.trim(), category: edit.category || null }),
      })
      if (!res.ok) throw new Error('Failed to update item')
      const updated = await res.json()
      setUsuals(prev => prev.map(u => u.id === edit.id ? updated : u))
      setEdit({ id: null, name: '', category: '' })
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

  const openAddToListDialog = async () => {
    let lists = []
    try {
      const res = await fetch('/api/working-lists')
      if (res.ok) lists = await res.json()
    } catch { /* use empty list */ }
    setDialog({ open: true, lists, submitting: false })
  }

  const handleAddToWorkingList = async (listIdOrCreate) => {
    setDialog(d => ({ ...d, submitting: true }))
    try {
      let workingListId = listIdOrCreate
      if (typeof listIdOrCreate === 'object' && listIdOrCreate.action === 'create') {
        const createRes = await fetch('/api/working-lists', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: listIdOrCreate.list_name }),
        })
        if (!createRes.ok) throw new Error('Failed to create list')
        const newList = await createRes.json()
        workingListId = newList.id
      }
      const res = await fetch('/api/usuals/add-to-working-list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usual_ids: Array.from(selected), working_list_id: workingListId }),
      })
      if (!res.ok) throw new Error('Failed to add to list')
      const data = await res.json()
      setDialog(d => ({ ...d, open: false, submitting: false }))
      setSelected(new Set())
      setSuccess(`Added ${data.added.length} item${data.added.length !== 1 ? 's' : ''} to shopping list`)
    } catch (e) {
      setError(e.message)
      setDialog(d => ({ ...d, submitting: false }))
    }
  }

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
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>Add Item</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <TextField
            size="small"
            label="Item name"
            value={addForm.name}
            onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            sx={{ flex: 2, minWidth: 150 }}
          />
          <FormControl size="small" sx={{ flex: 1, minWidth: 130 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={addForm.category}
              label="Category"
              onChange={e => setAddForm(f => ({ ...f, category: e.target.value }))}
            >
              <MenuItem value="">None</MenuItem>
              {CATEGORIES.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>
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

      {usuals.length > 0 && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {selected.size} of {usuals.length} selected
          </Typography>
          <Button size="small" onClick={() => setSelected(new Set(usuals.map(u => u.id)))}>All</Button>
          <Button size="small" onClick={() => setSelected(new Set())}>None</Button>
          <Box sx={{ flex: 1 }} />
          <Button
            variant="contained"
            color="secondary"
            startIcon={<NotificationsIcon />}
            disabled={selected.size === 0}
            onClick={openAddToListDialog}
          >
            Add {selected.size > 0 ? selected.size : ''} to List
          </Button>
        </Box>
      )}

      {usuals.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 6 }}>
          No items yet. Add your regular grocery items above.
        </Typography>
      ) : (
        Object.entries(grouped).map(([category, items]) => (
          <Accordion key={category} defaultExpanded disableGutters elevation={1} sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="medium">{category}</Typography>
              <Chip label={items.length} size="small" sx={{ ml: 1 }} />
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <List dense disablePadding>
                {items.map((item, idx) => (
                  <Box key={item.id}>
                    {idx > 0 && <Divider />}
                    <ListItem
                      secondaryAction={
                        edit.id !== item.id ? (
                          <Box>
                            <IconButton size="small" onClick={() => setEdit({ id: item.id, name: item.name, category: item.category || '' })}>
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
                      {edit.id === item.id ? (
                        <Box sx={{ display: 'flex', gap: 1, flex: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                          <TextField
                            size="small"
                            value={edit.name}
                            onChange={e => setEdit(s => ({ ...s, name: e.target.value }))}
                            onKeyDown={e => e.key === 'Enter' && handleSaveEdit()}
                            sx={{ flex: 2 }}
                          />
                          <FormControl size="small" sx={{ flex: 1, minWidth: 110 }}>
                            <InputLabel>Category</InputLabel>
                            <Select
                              value={edit.category}
                              label="Category"
                              onChange={e => setEdit(s => ({ ...s, category: e.target.value }))}
                            >
                              <MenuItem value="">None</MenuItem>
                              {CATEGORIES.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                            </Select>
                          </FormControl>
                          <IconButton size="small" color="primary" onClick={handleSaveEdit}>
                            <SaveIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => setEdit({ id: null, name: '', category: '' })}>
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

      <AddToWorkingListDialog
        open={dialog.open}
        onClose={() => setDialog(d => ({ ...d, open: false }))}
        itemCount={selected.size}
        workingLists={dialog.lists}
        onConfirm={handleAddToWorkingList}
        submitting={dialog.submitting}
      />
    </Box>
  )
}
