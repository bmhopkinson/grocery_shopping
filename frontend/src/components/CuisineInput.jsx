import { useState } from 'react'
import {
  Box,
  TextField,
  Button,
  Typography,
  Chip,
  Stack,
  Collapse,
  IconButton,
  Tabs,
  Tab,
} from '@mui/material'
import RestaurantIcon from '@mui/icons-material/Restaurant'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import LinkIcon from '@mui/icons-material/Link'
import { DEFAULT_RECIPE_SOURCES } from '../config'

const SUGGESTIONS = ['Italian', 'Mexican', 'Japanese', 'Indian', 'Thai', 'Mediterranean']

export default function CuisineInput({ onSubmit, loading }) {
  const [inputMode, setInputMode] = useState('search') // 'search' or 'url'
  const [cuisine, setCuisine] = useState('')
  const [recipeUrl, setRecipeUrl] = useState('')
  const [sources, setSources] = useState([...DEFAULT_RECIPE_SOURCES])
  const [newSource, setNewSource] = useState('')
  const [showSources, setShowSources] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (inputMode === 'url' && recipeUrl.trim()) {
      onSubmit({ directUrl: recipeUrl.trim() })
    } else if (inputMode === 'search' && cuisine.trim()) {
      onSubmit({ cuisine: cuisine.trim(), sources })
    }
  }

  const handleSuggestionClick = (suggestion) => {
    setCuisine(suggestion)
    onSubmit({ cuisine: suggestion, sources })
  }

  const isSubmitDisabled = loading ||
    (inputMode === 'search' && !cuisine.trim()) ||
    (inputMode === 'url' && !recipeUrl.trim())

  const handleRemoveSource = (sourceToRemove) => {
    setSources(sources.filter((s) => s !== sourceToRemove))
  }

  const handleAddSource = () => {
    const trimmed = newSource.trim().toLowerCase()
    if (trimmed && !sources.includes(trimmed)) {
      setSources([...sources, trimmed])
      setNewSource('')
    }
  }

  const handleSourceKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddSource()
    }
  }

  return (
    <Box>
      <Box sx={{ textAlign: 'center', mb: 3 }}>
        <RestaurantIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
        <Typography variant="h4" gutterBottom>
          Meal Planner
        </Typography>
      </Box>

      <Tabs
        value={inputMode}
        onChange={(e, v) => setInputMode(v)}
        centered
        sx={{ mb: 3 }}
      >
        <Tab icon={<SearchIcon />} label="Search by Cuisine" value="search" />
        <Tab icon={<LinkIcon />} label="Use Recipe URL" value="url" />
      </Tabs>

      <form onSubmit={handleSubmit}>
        {inputMode === 'search' ? (
          <>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
              What type of cuisine are you in the mood for?
            </Typography>
            <TextField
              fullWidth
              label="Enter a cuisine type"
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              disabled={loading}
              sx={{ mb: 2 }}
              placeholder="e.g., Italian, Mexican, Thai..."
            />
          </>
        ) : (
          <>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
              Paste a link to any recipe page
            </Typography>
            <TextField
              fullWidth
              label="Recipe URL"
              value={recipeUrl}
              onChange={(e) => setRecipeUrl(e.target.value)}
              disabled={loading}
              sx={{ mb: 2 }}
              placeholder="https://www.seriouseats.com/your-recipe..."
            />
          </>
        )}

        <Button
          type="submit"
          variant="contained"
          fullWidth
          size="large"
          disabled={isSubmitDisabled}
        >
          {loading
            ? (inputMode === 'search' ? 'Finding Recipes...' : 'Loading Recipe...')
            : (inputMode === 'search' ? 'Find Recipes' : 'Use This Recipe')}
        </Button>
      </form>

      {inputMode === 'search' && (
        <>
          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Or try one of these:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {SUGGESTIONS.map((suggestion) => (
                <Chip
                  key={suggestion}
                  label={suggestion}
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={loading}
                  clickable
                />
              ))}
            </Stack>
          </Box>

          <Box sx={{ mt: 3 }}>
            <Button
              size="small"
              onClick={() => setShowSources(!showSources)}
              endIcon={showSources ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ mb: 1 }}
            >
              Preferred Recipe Sources ({sources.length})
            </Button>

            <Collapse in={showSources}>
              <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Recipes will be searched from these sites:
                </Typography>

                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                  {sources.map((source) => (
                    <Chip
                      key={source}
                      label={source}
                      onDelete={() => handleRemoveSource(source)}
                      size="small"
                      disabled={loading}
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
                    onChange={(e) => setNewSource(e.target.value)}
                    onKeyDown={handleSourceKeyDown}
                    disabled={loading}
                    sx={{ flex: 1 }}
                  />
                  <IconButton
                    onClick={handleAddSource}
                    disabled={!newSource.trim() || loading}
                    color="primary"
                    size="small"
                  >
                    <AddIcon />
                  </IconButton>
                </Box>
              </Box>
            </Collapse>
          </Box>
        </>
      )}
    </Box>
  )
}
