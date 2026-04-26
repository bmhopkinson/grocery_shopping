import { useState, useEffect, useCallback } from 'react'
import {
  Box, List, ListItem, ListItemButton, ListItemText, ListItemSecondaryAction,
  Typography, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, CircularProgress, Alert, Divider, Paper,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'

export default function RecipesList({ onSelectRecipe }) {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [saving, setSaving] = useState(false)

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

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
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
    </Box>
  )
}
