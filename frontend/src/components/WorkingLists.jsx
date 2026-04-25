import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Typography,
  Button,
  TextField,
  Card,
  CardContent,
  CardActionArea,
  CardActions,
  Grid,
  IconButton,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import ListAltIcon from '@mui/icons-material/ListAlt'

export default function WorkingLists({ onSelectList }) {
  const [lists, setLists] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState({ open: false, list: null })

  const fetchLists = useCallback(async () => {
    try {
      const res = await fetch('/api/working-lists')
      if (!res.ok) throw new Error('Failed to load lists')
      setLists(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchLists() }, [fetchLists])

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await fetch('/api/working-lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() }),
      })
      if (!res.ok) throw new Error('Failed to create list')
      const created = await res.json()
      setLists(prev => [...prev, created])
      setNewName('')
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async () => {
    const list = deleteDialog.list
    setDeleteDialog({ open: false, list: null })
    try {
      const res = await fetch(`/api/working-lists/${list.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete list')
      setLists(prev => prev.filter(l => l.id !== list.id))
    } catch (e) {
      setError(e.message)
    }
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
      <Typography variant="h5" gutterBottom>My Shopping Lists</Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <TextField
          size="small"
          label="New list name"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleCreate()}
          sx={{ flex: 1 }}
        />
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
          disabled={!newName.trim() || creating}
        >
          Create
        </Button>
      </Box>

      {lists.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <ListAltIcon sx={{ fontSize: 56, color: 'text.disabled', mb: 1 }} />
          <Typography color="text.secondary">
            No shopping lists yet. Create one above.
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={2}>
          {lists.map(list => (
            <Grid item xs={12} sm={6} md={4} key={list.id}>
              <Card elevation={2}>
                <CardActionArea onClick={() => onSelectList(list)}>
                  <CardContent>
                    <Typography variant="h6" noWrap>{list.name}</Typography>
                    <Chip
                      label={`${list.item_count} item${list.item_count !== 1 ? 's' : ''}`}
                      size="small"
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </CardActionArea>
                <CardActions sx={{ justifyContent: 'flex-end', pt: 0 }}>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => setDeleteDialog({ open: true, list })}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, list: null })}>
        <DialogTitle>Delete list?</DialogTitle>
        <DialogContent>
          <Typography>
            Delete &ldquo;{deleteDialog.list?.name}&rdquo; and all its items? This cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, list: null })}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
