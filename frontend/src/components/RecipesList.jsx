import { useState, useEffect, useCallback } from 'react'
import {
  Box, Grid, Card, CardActionArea, CardContent, CardActions,
  Typography, Button, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, IconButton, CircularProgress, Alert,
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
      await fetch(`${API_BASE}/recipes/${recipe.id}`, { method: 'DELETE' })
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
        <Grid container spacing={2}>
          {recipes.map(recipe => (
            <Grid item xs={12} sm={6} md={4} key={recipe.id}>
              <Card elevation={2}>
                <CardActionArea onClick={() => onSelectRecipe(recipe)}>
                  <CardContent>
                    <Typography variant="h6" noWrap>{recipe.name}</Typography>
                    {recipe.url && (
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {recipe.url}
                      </Typography>
                    )}
                    {recipe.notes && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }} noWrap>
                        {recipe.notes}
                      </Typography>
                    )}
                  </CardContent>
                </CardActionArea>
                <CardActions sx={{ justifyContent: 'flex-end', pt: 0 }}>
                  <IconButton size="small" color="error" onClick={e => handleDelete(e, recipe)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
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
