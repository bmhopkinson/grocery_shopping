import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
} from '@mui/material'
import SortIcon from '@mui/icons-material/Sort'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'

export default function ReorderReminders() {
  const [lists, setLists] = useState([])
  const [selectedList, setSelectedList] = useState('')
  const [loading, setLoading] = useState(false)
  const [fetchingLists, setFetchingLists] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchLists() {
      try {
        const res = await fetch('/api/reminder-lists')
        if (!res.ok) throw new Error('Failed to fetch reminder lists')
        const data = await res.json()
        setLists(data.lists || [])
        if (data.lists?.length > 0) setSelectedList(data.lists[0])
      } catch (err) {
        setError(err.message)
      } finally {
        setFetchingLists(false)
      }
    }
    fetchLists()
  }, [])

  async function handleReorder() {
    if (!selectedList) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch('/api/reorder-reminders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ list_name: selectedList }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to reorder list')
      }
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Organize Shopping List
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Reorder a Reminders list by grocery store layout: produce → meat → canned &amp; dry goods →
        snacks → dairy → frozen → beer &amp; wine → paper items.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {fetchingLists ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      ) : (
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <FormControl sx={{ minWidth: 220 }} size="small">
            <InputLabel>Reminders List</InputLabel>
            <Select
              value={selectedList}
              label="Reminders List"
              onChange={(e) => { setSelectedList(e.target.value); setResult(null) }}
              disabled={loading}
            >
              {lists.map((l) => (
                <MenuItem key={l} value={l}>{l}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SortIcon />}
            onClick={handleReorder}
            disabled={!selectedList || loading}
          >
            {loading ? 'Organizing…' : 'Organize'}
          </Button>
        </Box>
      )}

      {result && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <CheckCircleOutlineIcon color="success" />
            <Typography variant="body1" color="success.main">
              Reordered {result.count} items in &ldquo;{result.list_name}&rdquo;
            </Typography>
          </Box>
          <Paper variant="outlined" sx={{ maxHeight: 360, overflow: 'auto' }}>
            <List dense disablePadding>
              {result.reordered_items.map((item, i) => (
                <Box key={i}>
                  {i > 0 && <Divider component="li" />}
                  <ListItem>
                    <ListItemText
                      primary={item}
                      primaryTypographyProps={{ variant: 'body2' }}
                      secondary={`#${i + 1}`}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                </Box>
              ))}
            </List>
          </Paper>
        </Box>
      )}
    </Box>
  )
}
