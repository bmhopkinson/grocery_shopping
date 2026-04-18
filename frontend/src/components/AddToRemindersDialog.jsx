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

export default function AddToRemindersDialog({ open, onClose, itemCount, reminderLists, onConfirm, submitting }) {
  const [selectedList, setSelectedList] = useState('')
  const [newListName, setNewListName] = useState('')

  useEffect(() => {
    if (open) {
      setSelectedList('')
      setNewListName('')
    }
  }, [open])

  const listName = newListName.trim() || selectedList

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Add to Reminders</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Adding {itemCount} item{itemCount !== 1 ? 's' : ''} to a Reminders list.
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
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={() => onConfirm(listName)}
          disabled={!listName || submitting}
        >
          {submitting ? 'Adding…' : 'Add to Reminders'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
