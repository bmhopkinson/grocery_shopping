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
import NotificationsIcon from '@mui/icons-material/Notifications'

export default function RemindersPrompt({ data, onSubmit, loading }) {
  const { items, existing_lists, instruction } = data
  const [selectedList, setSelectedList] = useState('')
  const [newListName, setNewListName] = useState('')

  const handleSubmit = () => {
    if (newListName.trim()) {
      onSubmit(newListName.trim())
    } else if (selectedList) {
      onSubmit(selectedList)
    }
  }

  const handleSkip = () => {
    onSubmit('skip')
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <NotificationsIcon color="primary" />
        <Typography variant="h5">Add to Reminders</Typography>
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

      {existing_lists && existing_lists.length > 0 && (
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Select existing list</InputLabel>
          <Select
            value={selectedList}
            label="Select existing list"
            onChange={(e) => {
              setSelectedList(e.target.value)
              setNewListName('')
            }}
          >
            {existing_lists.map((list) => (
              <MenuItem key={list} value={list}>
                {list}
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
        placeholder="e.g., Groceries, Weekly Shopping"
        value={newListName}
        onChange={(e) => {
          setNewListName(e.target.value)
          setSelectedList('')
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
          disabled={(!selectedList && !newListName.trim()) || loading}
          sx={{ flex: 2 }}
        >
          {loading ? 'Adding...' : 'Add to Reminders'}
        </Button>
      </Box>
    </Box>
  )
}
