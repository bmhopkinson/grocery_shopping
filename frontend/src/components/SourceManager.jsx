import { useState } from 'react'
import {
  Box,
  Button,
  Typography,
  Chip,
  Stack,
  Collapse,
  IconButton,
  TextField,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import AddIcon from '@mui/icons-material/Add'

export default function SourceManager({ sources, onChange, disabled }) {
  const [expanded, setExpanded] = useState(false)
  const [newSource, setNewSource] = useState('')

  const handleRemove = (source) => onChange(sources.filter(s => s !== source))

  const handleAdd = () => {
    const trimmed = newSource.trim().toLowerCase()
    if (trimmed && !sources.includes(trimmed)) {
      onChange([...sources, trimmed])
      setNewSource('')
    }
  }

  return (
    <Box sx={{ mt: 3 }}>
      <Button
        size="small"
        onClick={() => setExpanded(e => !e)}
        endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        sx={{ mb: 1 }}
      >
        Preferred Recipe Sources ({sources.length})
      </Button>

      <Collapse in={expanded}>
        <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Recipes will be searched from these sites:
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            {sources.map(source => (
              <Chip
                key={source}
                label={source}
                onDelete={() => handleRemove(source)}
                size="small"
                disabled={disabled}
              />
            ))}
            {sources.length === 0 && (
              <Typography variant="body2" color="text.secondary" fontStyle="italic">
                No sources selected (will search all sites)
              </Typography>
            )}
          </Stack>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              size="small"
              placeholder="Add a website (e.g., budgetbytes.com)"
              value={newSource}
              onChange={e => setNewSource(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAdd() } }}
              disabled={disabled}
              sx={{ flex: 1 }}
            />
            <IconButton onClick={handleAdd} disabled={!newSource.trim() || disabled} color="primary" size="small">
              <AddIcon />
            </IconButton>
          </Box>
        </Box>
      </Collapse>
    </Box>
  )
}
