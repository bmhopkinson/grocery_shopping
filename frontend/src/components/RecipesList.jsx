import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Box, Typography, Button, CircularProgress, Alert, Chip,
  Accordion, AccordionSummary, AccordionDetails,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, LinearProgress, Stack, Divider, List, ListItem,
  ListItemButton, ListItemText, ListItemAvatar, ListItemSecondaryAction,
  Avatar,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import LinkIcon from '@mui/icons-material/Link'

const LIMIT = 20

export default function RecipesList({ onSelectRecipe }) {
  const [groups, setGroups] = useState([])
  const [allTags, setAllTags] = useState([])
  const [selectedTags, setSelectedTags] = useState([])
  const [openGroups, setOpenGroups] = useState(new Set())
  const [groupData, setGroupData] = useState({}) // groupKey -> {recipes, total, loading}
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

  const groupKey = (id) => id ?? 'none'

  const fetchGroups = useCallback(async () => {
    const res = await fetch('/api/groups')
    if (!res.ok) throw new Error('Failed to load groups')
    return res.json()
  }, [])

  const fetchTags = useCallback(async () => {
    const res = await fetch('/api/recipes/tags')
    if (!res.ok) return []
    return res.json()
  }, [])

  useEffect(() => {
    Promise.all([fetchGroups(), fetchTags()])
      .then(([g, t]) => { setGroups(g); setAllTags(t) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [fetchGroups, fetchTags])

  // doFetch takes tags explicitly to avoid stale closure issues
  const doFetch = useCallback(async (id, offset, tags, replace) => {
    const key = groupKey(id)
    setGroupData(prev => ({
      ...prev,
      [key]: {
        recipes: replace ? [] : (prev[key]?.recipes ?? []),
        total: replace ? 0 : (prev[key]?.total ?? 0),
        loading: true,
      },
    }))

    const params = new URLSearchParams({ group_id: key, offset, limit: LIMIT })
    tags.forEach(t => params.append('tags', t))

    try {
      const res = await fetch(`/api/recipes?${params}`)
      if (!res.ok) throw new Error('Failed to load recipes')
      const data = await res.json()
      setGroupData(prev => {
        const existing = replace ? [] : (prev[key]?.recipes ?? [])
        return {
          ...prev,
          [key]: { recipes: [...existing, ...data.recipes], total: data.total, loading: false },
        }
      })
    } catch (e) {
      setError(e.message)
      setGroupData(prev => ({ ...prev, [key]: { ...(prev[key] ?? {}), loading: false } }))
    }
  }, [])

  const openGroupsRef = useRef(openGroups)
  useEffect(() => { openGroupsRef.current = openGroups }, [openGroups])

  const selectedTagsRef = useRef(selectedTags)
  useEffect(() => { selectedTagsRef.current = selectedTags }, [selectedTags])

  const toggleTag = (tag) => {
    setSelectedTags(prev => {
      const next = prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
      openGroupsRef.current.forEach(id => doFetch(id, 0, next, true))
      return next
    })
  }

  const toggleGroup = (id) => {
    setOpenGroups(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
        doFetch(id, 0, selectedTagsRef.current, true)
      }
      return next
    })
  }

  const loadMore = (id) => {
    const gd = groupData[groupKey(id)]
    if (!gd || gd.loading) return
    doFetch(id, gd.recipes.length, selectedTags, false)
  }

  const handleDelete = async (e, recipe) => {
    e.stopPropagation()
    if (!window.confirm(`Delete "${recipe.name}"?`)) return
    try {
      await fetch(`/api/recipes/${recipe.id}`, { method: 'DELETE' })
      const key = groupKey(recipe.group_id ?? null)
      setGroupData(prev => {
        const gd = prev[key]
        if (!gd) return prev
        return {
          ...prev,
          [key]: { ...gd, recipes: gd.recipes.filter(r => r.id !== recipe.id), total: gd.total - 1 },
        }
      })
      setGroups(prev => prev.map(g =>
        groupKey(g.id) === key ? { ...g, recipe_count: g.recipe_count - 1 } : g
      ))
    } catch (e) {
      setError(e.message)
    }
  }

  const refreshAfterCreate = async (created) => {
    const [newGroups, newTags] = await Promise.all([fetchGroups(), fetchTags()])
    setGroups(newGroups)
    setAllTags(newTags)
    const id = created.group_id ?? null
    const key = groupKey(id)
    setOpenGroups(prev => new Set([...prev, id]))
    doFetch(id, 0, selectedTags, true)
    onSelectRecipe(created)
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try {
      const res = await fetch('/api/recipes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), instructions: [] }),
      })
      if (!res.ok) throw new Error('Failed to create recipe')
      const created = await res.json()
      setDialogOpen(false)
      setNewName('')
      await refreshAfterCreate(created)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
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
                if (data.recipe) await refreshAfterCreate(data.recipe)
              } else if (currentEvent === 'error') {
                setExtractError(data.message)
              }
            } catch { /* ignore malformed SSE data */ }
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

      {allTags.length > 0 && (
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 2 }}>
          {allTags.map(tag => (
            <Chip
              key={tag}
              label={tag}
              size="small"
              onClick={() => toggleTag(tag)}
              color={selectedTags.includes(tag) ? 'primary' : 'default'}
              variant={selectedTags.includes(tag) ? 'filled' : 'outlined'}
            />
          ))}
        </Box>
      )}

      {groups.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No recipes yet. Add one to get started.
        </Typography>
      ) : (
        <Box>
          {groups.map(group => {
            const id = group.id ?? null
            const key = groupKey(id)
            const isOpen = openGroups.has(id)
            const gd = groupData[key]
            const hasMore = gd ? gd.recipes.length < gd.total : false

            return (
              <Accordion
                key={key}
                expanded={isOpen}
                onChange={() => toggleGroup(id)}
                disableGutters
                sx={{ '&:before': { display: 'none' }, border: '1px solid', borderColor: 'divider', mb: 1, borderRadius: 1 }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography fontWeight={500}>{group.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1.5, mt: '1px' }}>
                    {group.recipe_count} {group.recipe_count === 1 ? 'recipe' : 'recipes'}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 0 }}>
                  {gd?.loading && gd.recipes.length === 0 && (
                    <LinearProgress />
                  )}
                  {gd?.recipes?.length === 0 && !gd.loading && (
                    <Typography color="text.secondary" variant="body2" sx={{ px: 2, py: 1.5 }}>
                      No recipes match the selected tags.
                    </Typography>
                  )}
                  {gd?.recipes?.length > 0 && (
                    <List disablePadding>
                      {gd.recipes.map((recipe, idx) => (
                        <Box key={recipe.id}>
                          {idx > 0 && <Divider />}
                          <ListItem disablePadding>
                            <ListItemButton onClick={() => onSelectRecipe(recipe)}>
                              <ListItemAvatar>
                                <Avatar
                                  variant="rounded"
                                  src={`/api/recipes/${recipe.id}/image`}
                                  imgProps={{ onError: e => { e.currentTarget.style.display = 'none' } }}
                                  sx={{ width: 44, height: 44, mr: 1 }}
                                />
                              </ListItemAvatar>
                              <ListItemText
                                primary={recipe.name}
                                secondary={
                                  <Box component="span" sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                    {(recipe.notes || recipe.url) && (
                                      <Typography component="span" variant="body2" color="text.secondary" noWrap>
                                        {recipe.notes || recipe.url}
                                      </Typography>
                                    )}
                                    {recipe.tags?.length > 0 && (
                                      <Box component="span" sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                        {recipe.tags.map(tag => (
                                          <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
                                        ))}
                                      </Box>
                                    )}
                                  </Box>
                                }
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
                  )}
                  {hasMore && (
                    <Box sx={{ px: 2, py: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                      <Button
                        size="small"
                        onClick={() => loadMore(id)}
                        disabled={gd?.loading}
                        startIcon={gd?.loading ? <CircularProgress size={14} /> : null}
                      >
                        {gd?.loading ? 'Loading…' : `Load more (${gd.total - gd.recipes.length} remaining)`}
                      </Button>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            )
          })}
        </Box>
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
                  <Typography key={i} variant="body2" color="text.secondary">{msg}</Typography>
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
