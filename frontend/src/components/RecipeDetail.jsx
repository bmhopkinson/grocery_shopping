import { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, TextField, Button, Divider, List, ListItem,
  ListItemText, ListItemSecondaryAction, IconButton, CircularProgress,
  Alert, Paper, Stack, Autocomplete, Chip,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import AddToWorkingListDialog from './AddToWorkingListDialog'

function IngredientRow({ ingredient, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(ingredient.name)
  const [amount, setAmount] = useState(ingredient.amount)
  const [unit, setUnit] = useState(ingredient.unit)

  const save = async () => {
    await onUpdate(ingredient.id, { name, amount, unit })
    setEditing(false)
  }

  const cancel = () => {
    setName(ingredient.name)
    setAmount(ingredient.amount)
    setUnit(ingredient.unit)
    setEditing(false)
  }

  if (editing) {
    return (
      <ListItem sx={{ gap: 1, flexWrap: 'wrap', py: 1 }}>
        <TextField size="small" label="Name" value={name} onChange={e => setName(e.target.value)} sx={{ flex: '1 1 140px' }} />
        <TextField size="small" label="Amount" value={amount} onChange={e => setAmount(e.target.value)} sx={{ width: 80 }} />
        <TextField size="small" label="Unit" value={unit} onChange={e => setUnit(e.target.value)} sx={{ width: 90 }} />
        <IconButton size="small" color="primary" onClick={save}><CheckIcon /></IconButton>
        <IconButton size="small" onClick={cancel}><CloseIcon /></IconButton>
      </ListItem>
    )
  }

  const label = [ingredient.amount, ingredient.unit].filter(Boolean).join(' ')
  return (
    <ListItem>
      <ListItemText
        primary={ingredient.name}
        secondary={label || undefined}
      />
      <ListItemSecondaryAction>
        <IconButton size="small" onClick={() => setEditing(true)}><EditIcon fontSize="small" /></IconButton>
        <IconButton size="small" color="error" onClick={() => onDelete(ingredient.id)}><DeleteIcon fontSize="small" /></IconButton>
      </ListItemSecondaryAction>
    </ListItem>
  )
}

function InstructionRow({ step, index, onChange, onDelete }) {
  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mb: 1 }}>
      <Typography sx={{ mt: 1.5, minWidth: 24, color: 'text.secondary' }}>{index + 1}.</Typography>
      <TextField
        multiline
        fullWidth
        size="small"
        value={step}
        onChange={e => onChange(index, e.target.value)}
      />
      <IconButton size="small" color="error" onClick={() => onDelete(index)} sx={{ mt: 0.5 }}>
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Box>
  )
}

export default function RecipeDetail({ recipeId }) {
  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  // Editable fields
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [instructions, setInstructions] = useState([])
  const [groupValue, setGroupValue] = useState(null) // null | {id, name} | string (new name)
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [dirty, setDirty] = useState(false)

  const [groups, setGroups] = useState([])
  const fetchGroups = useCallback(() => {
    fetch('/api/groups').then(r => r.ok ? r.json() : []).then(setGroups).catch(() => {})
  }, [])
  useEffect(() => { fetchGroups() }, [fetchGroups])

  // Add to working list
  const [listDialog, setListDialog] = useState({ open: false, lists: [], submitting: false })

  const handleOpenListDialog = async () => {
    const res = await fetch('/api/working-lists')
    const lists = res.ok ? await res.json() : []
    setListDialog({ open: true, lists, submitting: false })
  }

  const handleAddToList = async (selection) => {
    setListDialog(prev => ({ ...prev, submitting: true }))
    try {
      let listId = selection
      if (selection?.action === 'create') {
        const res = await fetch('/api/working-lists', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: selection.list_name }),
        })
        if (!res.ok) throw new Error('Failed to create list')
        const created = await res.json()
        listId = created.id
      }
      const ingredients = recipe.ingredients || []
      await Promise.all(ingredients.map(ing =>
        fetch(`/api/working-lists/${listId}/items`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: ing.name, amount: ing.amount, unit: ing.unit }),
        })
      ))
      setListDialog({ open: false, lists: [], submitting: false })
    } catch (e) {
      setError(e.message)
      setListDialog(prev => ({ ...prev, submitting: false }))
    }
  }

  // New ingredient form
  const [newIngName, setNewIngName] = useState('')
  const [newIngAmount, setNewIngAmount] = useState('')
  const [newIngUnit, setNewIngUnit] = useState('')
  const [addingIng, setAddingIng] = useState(false)

  const fetchRecipe = useCallback(async () => {
    try {
      const res = await fetch(`/api/recipes/${recipeId}`)
      if (!res.ok) throw new Error('Failed to load recipe')
      const data = await res.json()
      setRecipe(data)
      setName(data.name)
      setUrl(data.url || '')
      setNotes(data.notes || '')
      setInstructions(data.instructions || [])
      setGroupValue(data.group || null)
      setTags(data.tags || [])
      setDirty(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [recipeId])

  useEffect(() => { fetchRecipe() }, [fetchRecipe])

  const saveRecipe = async () => {
    setSaving(true)
    try {
      let resolvedGroupId = null
      if (typeof groupValue === 'string' && groupValue.trim()) {
        const res = await fetch('/api/groups', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: groupValue.trim() }),
        })
        if (!res.ok) throw new Error('Failed to create group')
        const created = await res.json()
        resolvedGroupId = created.id
        setGroupValue(created)
        fetchGroups()
      } else if (groupValue?.id) {
        resolvedGroupId = groupValue.id
      }

      const res = await fetch(`/api/recipes/${recipeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, url: url || null, notes: notes || null, instructions, tags, group_id: resolvedGroupId }),
      })
      if (!res.ok) throw new Error('Failed to save')
      setDirty(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase()
    if (!trimmed || tags.includes(trimmed)) { setTagInput(''); return }
    setTags(prev => [...prev, trimmed])
    setTagInput('')
    setDirty(true)
  }

  const handleRemoveTag = (tag) => {
    setTags(prev => prev.filter(t => t !== tag))
    setDirty(true)
  }

  const handleInstructionChange = (index, value) => {
    setInstructions(prev => { const next = [...prev]; next[index] = value; return next })
    setDirty(true)
  }

  const handleInstructionDelete = (index) => {
    setInstructions(prev => prev.filter((_, i) => i !== index))
    setDirty(true)
  }

  const handleAddStep = () => {
    setInstructions(prev => [...prev, ''])
    setDirty(true)
  }

  const handleAddIngredient = async () => {
    if (!newIngName.trim()) return
    setAddingIng(true)
    try {
      const res = await fetch(`/api/recipes/${recipeId}/ingredients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newIngName.trim(), amount: newIngAmount, unit: newIngUnit }),
      })
      if (!res.ok) throw new Error('Failed to add ingredient')
      const added = await res.json()
      setRecipe(prev => ({ ...prev, ingredients: [...(prev.ingredients || []), added] }))
      setNewIngName('')
      setNewIngAmount('')
      setNewIngUnit('')
    } catch (e) {
      setError(e.message)
    } finally {
      setAddingIng(false)
    }
  }

  const handleUpdateIngredient = async (ingredientId, fields) => {
    const res = await fetch(`/api/recipes/${recipeId}/ingredients/${ingredientId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields),
    })
    if (!res.ok) { setError('Failed to update ingredient'); return }
    const updated = await res.json()
    setRecipe(prev => ({
      ...prev,
      ingredients: prev.ingredients.map(i => i.id === ingredientId ? updated : i),
    }))
  }

  const handleDeleteIngredient = async (ingredientId) => {
    await fetch(`/api/recipes/${recipeId}/ingredients/${ingredientId}`, { method: 'DELETE' })
    setRecipe(prev => ({ ...prev, ingredients: prev.ingredients.filter(i => i.id !== ingredientId) }))
  }

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
  if (!recipe) return <Alert severity="error">Recipe not found</Alert>

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box
        component="img"
        src={`/api/recipes/${recipeId}/image`}
        alt={name}
        onError={e => { e.currentTarget.style.display = 'none' }}
        sx={{ width: '100%', maxHeight: 300, objectFit: 'cover', borderRadius: 1, mb: 2, display: 'block' }}
      />

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Stack spacing={2}>
          <TextField
            label="Name"
            fullWidth
            value={name}
            onChange={e => { setName(e.target.value); setDirty(true) }}
          />
          <TextField
            label="URL"
            fullWidth
            value={url}
            onChange={e => { setUrl(e.target.value); setDirty(true) }}
          />
          <TextField
            label="Notes"
            fullWidth
            multiline
            minRows={2}
            value={notes}
            onChange={e => { setNotes(e.target.value); setDirty(true) }}
          />
          <Autocomplete
            freeSolo
            options={groups}
            getOptionLabel={g => typeof g === 'string' ? g : g.name}
            value={groupValue}
            onChange={(_, v) => { setGroupValue(v); setDirty(true) }}
            onInputChange={(_, v, reason) => { if (reason === 'input') { setGroupValue(v || null); setDirty(true) } }}
            isOptionEqualToValue={(o, v) => o.id === v?.id}
            renderInput={params => <TextField {...params} label="Group" placeholder="e.g. Italian, Asian, Desserts" helperText="Pick existing or type a new group name" />}
          />
          <Box>
            <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              {tags.map(tag => (
                <Chip
                  key={tag}
                  label={tag}
                  size="small"
                  icon={<LocalOfferIcon />}
                  onDelete={() => handleRemoveTag(tag)}
                />
              ))}
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                size="small"
                label="Add tag"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAddTag()}
                sx={{ flex: 1 }}
              />
              <Button variant="outlined" size="small" onClick={handleAddTag} disabled={!tagInput.trim()}>
                Add
              </Button>
            </Box>
          </Box>
        </Stack>
      </Paper>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="h6">Ingredients</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<ShoppingCartIcon />}
          onClick={handleOpenListDialog}
          disabled={!(recipe.ingredients?.length)}
        >
          Add to List
        </Button>
      </Box>
      <Paper variant="outlined" sx={{ mb: 3 }}>
        <List dense disablePadding>
          {(recipe.ingredients || []).map(ing => (
            <IngredientRow
              key={ing.id}
              ingredient={ing}
              onUpdate={handleUpdateIngredient}
              onDelete={handleDeleteIngredient}
            />
          ))}
        </List>
        <Divider />
        <Box sx={{ display: 'flex', gap: 1, p: 1.5, flexWrap: 'wrap' }}>
          <TextField
            size="small"
            label="Name"
            value={newIngName}
            onChange={e => setNewIngName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddIngredient()}
            sx={{ flex: '1 1 140px' }}
          />
          <TextField
            size="small"
            label="Amount"
            value={newIngAmount}
            onChange={e => setNewIngAmount(e.target.value)}
            sx={{ width: 80 }}
          />
          <TextField
            size="small"
            label="Unit"
            value={newIngUnit}
            onChange={e => setNewIngUnit(e.target.value)}
            sx={{ width: 90 }}
          />
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddIngredient}
            disabled={!newIngName.trim() || addingIng}
          >
            Add
          </Button>
        </Box>
      </Paper>

      <Typography variant="h6" gutterBottom>Instructions</Typography>
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        {instructions.length === 0 && (
          <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>No steps yet.</Typography>
        )}
        {instructions.map((step, i) => (
          <InstructionRow
            key={i}
            index={i}
            step={step}
            onChange={handleInstructionChange}
            onDelete={handleInstructionDelete}
          />
        ))}
        <Button startIcon={<AddIcon />} size="small" onClick={handleAddStep} sx={{ mt: 1 }}>
          Add Step
        </Button>
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={saveRecipe}
          disabled={!dirty || saving}
        >
          {saving ? 'Saving…' : 'Save Changes'}
        </Button>
      </Box>

      <AddToWorkingListDialog
        open={listDialog.open}
        onClose={() => setListDialog(prev => ({ ...prev, open: false }))}
        itemCount={recipe.ingredients?.length || 0}
        workingLists={listDialog.lists}
        onConfirm={handleAddToList}
        submitting={listDialog.submitting}
      />
    </Box>
  )
}
