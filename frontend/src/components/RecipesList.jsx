import { useState, useEffect, useCallback } from 'react'
import {
  Box, List, ListItem, ListItemButton, ListItemText, ListItemSecondaryAction,
  ListItemAvatar, Avatar, Typography, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, CircularProgress, Alert, Divider, Paper,
  LinearProgress, Stack,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import LinkIcon from '@mui/icons-material/Link'

export default function RecipesList({ onSelectRecipe }) {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // New recipe dialog
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [saving, setSaving] = useState(false)

  // Extract from URL dialog
  const [urlDialogOpen, setUrlDialogOpen] = useState(false)
  const [extractUrl, setExtractUrl] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [extractStatus, setExtractStatus] = useState([])
  const [extractError, setExtractError] = useState(null)

  const fetchRecipes = useCallback(async () => {
    try {
      const res = await fetch(`/api/recipes`)
      if (!res.ok) throw new Error('Failed to load recipes')
      setRecipes(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRecipes() }, [fetchRecipes])

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try {
      const res = await fetch(`/api/recipes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), instructions: [] }),
      })
      if (!res.ok) throw new Error('Failed to create recipe')
      const created = await res.json()
      setDialogOpen(false)
      setNewName('')
      onSelectRecipe(created)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (e, recipe) => {
    e.stopPropagation()
    if (!window.confirm(`Delete "${recipe.name}"?`)) return
    try {
      await fetch(`/api/recipes/${recipe.id}`, { method: 'DELETE' })
      setRecipes(prev => prev.filter(r => r.id !== recipe.id))
    } catch (e) {
      setError(e.message)
    }
  }

  const handleExtractFromUrl = async () => {
    if (!extractUrl.trim()) return
    setExtracting(true)
    setExtractStatus([])
    setExtractError(null)

    try {
      const res = await fetch('/api/recipes/extract-from-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: extractUrl.trim() }),
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
              if (currentEvent === 'status') {
                setExtractStatus(prev => [...prev, data.message])
              } else if (currentEvent === 'recipe_extracted') {
                setUrlDialogOpen(false)
                setExtractUrl('')
                setExtractStatus([])
                await fetchRecipes()
                if (data.recipe) onSelectRecipe(data.recipe)
              } else if (currentEvent === 'error') {
                setExtractError(data.message)
              }
            } catch {
              // ignore malformed SSE data lines
            }
          }
        }
      }
    } catch (e) {
      setExtractError(e.message)
    } finally {
      setExtracting(false)
    }
  }

  const handleUrlDialogClose = () => {
    if (extracting) return
    setUrlDialogOpen(false)
    setExtractUrl('')
    setExtractStatus([])
    setExtractError(null)
  }

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
        <Button variant="outlined" startIcon={<LinkIcon />} onClick={() => setUrlDialogOpen(true)}>
          Add from URL
        </Button>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          New Recipe
        </Button>
      </Box>

      {recipes.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No recipes yet. Add one to get started.
        </Typography>
      ) : (
        <Paper variant="outlined">
          <List disablePadding>
            {recipes.map((recipe, index) => (
              <Box key={recipe.id}>
                {index > 0 && <Divider />}
                <ListItem disablePadding>
                  <ListItemButton onClick={() => onSelectRecipe(recipe)}>
                    <ListItemAvatar>
                      <Avatar
                        variant="rounded"
                        src={`/api/recipes/${recipe.id}/image`}
                        imgProps={{ onError: e => { e.currentTarget.style.display = 'none' } }}
                        sx={{ width: 48, height: 48, mr: 1 }}
                      />
                    </ListItemAvatar>
                    <ListItemText
                      primary={recipe.name}
                      secondary={recipe.notes || recipe.url || undefined}
                      secondaryTypographyProps={{ noWrap: true }}
                    />
                  </ListItemButton>
                  <ListItemSecondaryAction>
                    <IconButton size="small" color="error" onClick={e => handleDelete(e, recipe)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              </Box>
            ))}
          </List>
        </Paper>
      )}

      {/* New recipe dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>New Recipe</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Recipe name"
            fullWidth
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDialogOpen(false); setNewName('') }}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!newName.trim() || saving}>
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Extract from URL dialog */}
      <Dialog open={urlDialogOpen} onClose={handleUrlDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>Add Recipe from URL</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Recipe URL"
            placeholder="https://www.example.com/recipes/..."
            fullWidth
            value={extractUrl}
            onChange={e => setExtractUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !extracting && handleExtractFromUrl()}
            disabled={extracting}
            sx={{ mt: 1 }}
          />

          {extracting && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress sx={{ mb: 1.5 }} />
              <Stack spacing={0.5}>
                {extractStatus.map((msg, i) => (
                  <Typography key={i} variant="body2" color="text.secondary">
                    {msg}
                  </Typography>
                ))}
              </Stack>
            </Box>
          )}

          {extractError && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setExtractError(null)}>
              {extractError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleUrlDialogClose} disabled={extracting}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleExtractFromUrl}
            disabled={!extractUrl.trim() || extracting}
            startIcon={extracting ? <CircularProgress size={16} /> : <LinkIcon />}
          >
            {extracting ? 'Extracting…' : 'Extract Recipe'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
