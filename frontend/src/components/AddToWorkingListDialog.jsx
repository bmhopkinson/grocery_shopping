import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
} from '@mui/material'

export default function AddToWorkingListDialog({ open, onClose, itemCount, workingLists, onConfirm, submitting }) {
  const [selectedId, setSelectedId] = useState('')
  const [newListName, setNewListName] = useState('')

  useEffect(() => {
    if (open) {
      setSelectedId(workingLists[0]?.id || '')
      setNewListName('')
    }
  }, [open, workingLists])

  const handleConfirm = () => {
    if (newListName.trim()) {
      // Need to create new list first — signal caller with a sentinel
      onConfirm({ action: 'create', list_name: newListName.trim() })
    } else if (selectedId) {
      onConfirm(selectedId)
    }
  }

  const canSubmit = (selectedId && !newListName.trim()) || newListName.trim()

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Add to Shopping List</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Adding {itemCount} item{itemCount !== 1 ? 's' : ''} to a shopping list.
        </Typography>
        {workingLists.length > 0 && (
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Select existing list</InputLabel>
            <Select
              value={selectedId}
              label="Select existing list"
              onChange={e => { setSelectedId(e.target.value); setNewListName('') }}
            >
              {workingLists.map(l => <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>)}
            </Select>
          </FormControl>
        )}
        <TextField
          fullWidth
          label={workingLists.length > 0 ? 'Or create new list' : 'New list name'}
          value={newListName}
          onChange={e => { setNewListName(e.target.value); setSelectedId('') }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={!canSubmit || submitting}
        >
          {submitting ? 'Adding…' : 'Add to List'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
