import { useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider,
  Alert,
  Link,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import BookmarkAddedIcon from '@mui/icons-material/BookmarkAdded'

async function extractAndSaveRecipe(url, onStatus) {
  const res = await fetch('/api/recipes/extract-from-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Extraction failed')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        try {
          const data = JSON.parse(line.slice(5).trim())
          if (currentEvent === 'status') onStatus(data.message)
          else if (currentEvent === 'recipe_extracted') return data.recipe
          else if (currentEvent === 'error') throw new Error(data.message)
        } catch (e) {
          if (e.message !== 'Unexpected end of JSON input') throw e
        }
      }
    }
  }
  throw new Error('Recipe extraction completed but no recipe was saved')
}

export default function CompletionScreen({ data, onReset }) {
  const { selected_meal, grocery_list, reminders_added } = data
  const [saveState, setSaveState] = useState('idle') // 'idle' | 'saving' | 'saved' | 'error'
  const [savedRecipeId, setSavedRecipeId] = useState(null)
  const [saveStatus, setSaveStatus] = useState('')

  async function handleSave() {
    setSaveState('saving')
    setSaveStatus('')
    try {
      const recipe = await extractAndSaveRecipe(
        selected_meal.recipe_url,
        msg => setSaveStatus(msg),
      )
      setSavedRecipeId(recipe.id)
      setSaveState('saved')
    } catch (e) {
      setSaveStatus(e.message)
      setSaveState('error')
    }
  }

  return (
    <Box>
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <CheckCircleIcon sx={{ fontSize: 60, color: 'success.main', mb: 2 }} />
        <Typography variant="h4" gutterBottom>
          All Done!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Your meal planning is complete.
        </Typography>
      </Box>

      {selected_meal && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" gutterBottom>
                  Selected Recipe
                </Typography>
                <Typography variant="h5" color="primary.main" gutterBottom>
                  {selected_meal.name}
                </Typography>
                {selected_meal.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {selected_meal.description}
                  </Typography>
                )}
              </Box>
              <Button
                variant={saveState === 'saved' ? 'outlined' : 'contained'}
                size="small"
                startIcon={saveState === 'saved' ? <BookmarkAddedIcon /> : <BookmarkAddIcon />}
                onClick={handleSave}
                disabled={saveState === 'saving' || saveState === 'saved' || !selected_meal.recipe_url}
                color={saveState === 'saved' ? 'success' : 'primary'}
                sx={{ whiteSpace: 'nowrap', flexShrink: 0 }}
              >
                {saveState === 'saving' ? 'Saving…' : saveState === 'saved' ? 'Saved' : 'Save to Recipes'}
              </Button>
            </Box>

            {saveState === 'saving' && saveStatus && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {saveStatus}
              </Typography>
            )}
            {saveState === 'error' && (
              <Alert severity="error" sx={{ mt: 1 }} onClose={() => setSaveState('idle')}>
                {saveStatus || 'Failed to save recipe. Try again.'}
              </Alert>
            )}
            {saveState === 'saved' && savedRecipeId && (
              <Alert severity="success" sx={{ mt: 1 }}>
                Recipe saved.{' '}
                <Link href={`/recipes/${savedRecipeId}`}>View in Recipes</Link>
              </Alert>
            )}

            {selected_meal.recipe_url && (
              <Box sx={{ mt: 2 }}>
                <Link
                  href={selected_meal.recipe_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                >
                  View Full Recipe <OpenInNewIcon fontSize="small" />
                </Link>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Grocery List ({grocery_list.length} items)
          </Typography>
          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
            {grocery_list.map((item, idx) => (
              <ListItem key={idx} dense>
                <ListItemText
                  primary={item.name}
                  secondary={[item.amount, item.unit].filter(Boolean).join(' ') || null}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      {reminders_added !== null && (
        <Alert
          severity={reminders_added ? 'success' : 'info'}
          sx={{ mb: 3 }}
        >
          {reminders_added
            ? 'Items have been added to your Reminders app!'
            : 'Items were not added to Reminders.'}
        </Alert>
      )}

      <Divider sx={{ my: 3 }} />

      <Button
        variant="contained"
        fullWidth
        size="large"
        onClick={onReset}
      >
        Find Another Meal
      </Button>
    </Box>
  )
}
