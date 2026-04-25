import { useState } from 'react'
import {
  Box,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  List,
  ListItem,
  ListItemText,
  Paper,
  Divider,
} from '@mui/material'
import ListAltIcon from '@mui/icons-material/ListAlt'

export default function RemindersPrompt({ data, onSubmit, loading }) {
  const { items, working_lists = [], instruction } = data
  const [selectedListId, setSelectedListId] = useState(working_lists[0]?.id || '')
  const [newListName, setNewListName] = useState('')

  const handleSubmit = () => {
    if (newListName.trim()) {
      onSubmit({ action: 'create', list_name: newListName.trim() })
    } else if (selectedListId) {
      onSubmit({ action: 'select', list_id: selectedListId })
    }
  }

  const handleSkip = () => {
    onSubmit('skip')
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <ListAltIcon color="primary" />
        <Typography variant="h5">Add to Shopping List</Typography>
      </Box>

      {instruction && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {instruction}
        </Typography>
      )}

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Items to add ({items.length}):
        </Typography>
        <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
          {items.map((item, idx) => (
            <ListItem key={idx} dense>
              <ListItemText
                primary={item.name}
                secondary={`${item.amount} ${item.unit}`.trim()}
              />
            </ListItem>
          ))}
        </List>
      </Paper>

      <Divider sx={{ my: 2 }} />

      {working_lists.length > 0 && (
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Select existing list</InputLabel>
          <Select
            value={selectedListId}
            label="Select existing list"
            onChange={(e) => {
              setSelectedListId(e.target.value)
              setNewListName('')
            }}
          >
            {working_lists.map((list) => (
              <MenuItem key={list.id} value={list.id}>
                {list.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Or create a new list:
      </Typography>

      <TextField
        fullWidth
        label="New list name"
        placeholder="e.g., Weekly Groceries"
        value={newListName}
        onChange={(e) => {
          setNewListName(e.target.value)
          setSelectedListId('')
        }}
        sx={{ mb: 3 }}
      />

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="outlined"
          size="large"
          onClick={handleSkip}
          disabled={loading}
          sx={{ flex: 1 }}
        >
          Skip
        </Button>
        <Button
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={(!selectedListId && !newListName.trim()) || loading}
          sx={{ flex: 2 }}
        >
          {loading ? 'Saving…' : 'Add to List'}
        </Button>
      </Box>
    </Box>
  )
}
