import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Accordion, AccordionSummary, AccordionDetails,
  Box, Typography, List, ListItem, ListItemText,
  IconButton, TextField, Select, MenuItem, FormControl, InputLabel,
  Button, Chip, Alert, Tooltip, Grid, Collapse,
  Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import SaveIcon from '@mui/icons-material/Save'
import CancelIcon from '@mui/icons-material/Cancel'
import AddIcon from '@mui/icons-material/Add'
import LinkIcon from '@mui/icons-material/Link'

const DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
const DAY_ABBR = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']

function getCurrentWeekStart() {
  const today = new Date()
  // getDay(): 0=Sun,1=Mon,...,6=Sat. Saturday=6, so diff back to Saturday:
  const day = today.getDay()
  const diff = day === 6 ? 0 : -(day + 1)
  const saturday = new Date(today)
  saturday.setDate(today.getDate() + diff)
  return saturday.toISOString().split('T')[0]
}

function weekLabel(weekStart) {
  const start = new Date(weekStart + 'T00:00:00')
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  const opts = { month: 'short', day: 'numeric' }
  return `${start.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', { ...opts, year: 'numeric' })}`
}

const EMPTY_ADD = { name: '', day_of_week: 0, notes: '', url: '' }

export default function WeeklyPlanner() {
  const [meals, setMeals] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState(EMPTY_ADD)
  const [submitting, setSubmitting] = useState(false)
  const [editId, setEditId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [deleteId, setDeleteId] = useState(null)
  const [expandedMeals, setExpandedMeals] = useState(new Set())

  const currentWeekStart = getCurrentWeekStart()

  const toggleMealExpanded = (id) => {
    setExpandedMeals(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const [expanded, setExpanded] = useState(() => new Set([currentWeekStart]))

  const fetchMeals = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/weekly-meals')
      if (!res.ok) throw new Error(await res.text())
      setMeals(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchMeals() }, [fetchMeals])

  // Group meals by week, always include current week even if empty
  const weekGroups = useMemo(() => {
    const groups = { [currentWeekStart]: [] }
    for (const meal of meals) {
      if (!groups[meal.week_start]) groups[meal.week_start] = []
      groups[meal.week_start].push(meal)
    }
    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => a.day_of_week - b.day_of_week)
    }
    return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
  }, [meals, currentWeekStart])

  const toggleExpanded = (weekStart) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(weekStart)) next.delete(weekStart)
      else next.add(weekStart)
      return next
    })
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!addForm.name.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/weekly-meals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...addForm, week_start: currentWeekStart }),
      })
      if (!res.ok) throw new Error(await res.text())
      const created = await res.json()
      setMeals(prev => [...prev, created])
      setAddForm(EMPTY_ADD)
      setShowAdd(false)
      setSuccess('Meal added')
      setTimeout(() => setSuccess(null), 3000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const startEdit = (meal) => {
    setEditId(meal.id)
    setEditForm({ name: meal.name, day_of_week: meal.day_of_week, notes: meal.notes || '', url: meal.url || '' })
  }

  const handleUpdate = async () => {
    if (!editForm.name.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch(`/api/weekly-meals/${editId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      })
      if (!res.ok) throw new Error(await res.text())
      const updated = await res.json()
      setMeals(prev => prev.map(m => m.id === editId ? updated : m))
      setEditId(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      const res = await fetch(`/api/weekly-meals/${deleteId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      setMeals(prev => prev.filter(m => m.id !== deleteId))
      setDeleteId(null)
    } catch (e) {
      setError(e.message)
      setDeleteId(null)
    }
  }

  const mealToDelete = deleteId ? meals.find(m => m.id === deleteId) : null

  return (
    <Box>
      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {weekGroups.map(([weekStart, weekMeals]) => {
        const isCurrent = weekStart === currentWeekStart
        return (
          <Accordion
            key={weekStart}
            expanded={expanded.has(weekStart)}
            onChange={() => toggleExpanded(weekStart)}
            sx={{ mb: 1 }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%', pr: 1 }}>
                <Typography fontWeight={isCurrent ? 600 : 400}>
                  {isCurrent ? 'This Week' : 'Week of'} · {weekLabel(weekStart)}
                </Typography>
                {isCurrent && <Chip label="current" size="small" color="primary" variant="outlined" />}
                {weekMeals.length > 0 && (
                  <Chip label={weekMeals.length} size="small" sx={{ ml: 'auto' }} />
                )}
              </Box>
            </AccordionSummary>

            <AccordionDetails sx={{ pt: 0 }}>
              {weekMeals.length === 0 ? (
                <Typography color="text.secondary" variant="body2" sx={{ py: 1 }}>
                  {isCurrent ? 'No meals planned yet.' : 'No meals planned.'}
                </Typography>
              ) : (
                <Box>
                  {weekMeals.map((meal) =>
                    editId === meal.id ? (
                      <Box key={meal.id} sx={{ borderBottom: '1px solid', borderColor: 'divider', p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Grid container spacing={1}>
                          <Grid item xs={12} sm={3}>
                            <FormControl fullWidth size="small">
                              <InputLabel>Day</InputLabel>
                              <Select
                                value={editForm.day_of_week}
                                label="Day"
                                onChange={e => setEditForm(f => ({ ...f, day_of_week: e.target.value }))}
                              >
                                {DAYS.map((d, i) => <MenuItem key={d} value={i}>{d}</MenuItem>)}
                              </Select>
                            </FormControl>
                          </Grid>
                          <Grid item xs={12} sm={9}>
                            <TextField
                              fullWidth size="small" label="Meal name"
                              value={editForm.name}
                              onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                            />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField
                              fullWidth size="small" label="Notes"
                              value={editForm.notes}
                              onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))}
                            />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField
                              fullWidth size="small" label="URL (optional)"
                              value={editForm.url}
                              onChange={e => setEditForm(f => ({ ...f, url: e.target.value }))}
                            />
                          </Grid>
                        </Grid>
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                          <IconButton size="small" color="primary" onClick={handleUpdate} disabled={submitting || !editForm.name.trim()}>
                            <SaveIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => setEditId(null)}>
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                    ) : (
                      <Box key={meal.id} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
                        <ListItem
                          disablePadding={false}
                          secondaryAction={
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              {meal.notes && (
                                <Tooltip title={expandedMeals.has(meal.id) ? 'Hide note' : 'Show note'}>
                                  <IconButton size="small" onClick={() => toggleMealExpanded(meal.id)}>
                                    {expandedMeals.has(meal.id) ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                                  </IconButton>
                                </Tooltip>
                              )}
                              {meal.url && (
                                <Tooltip title="Open recipe">
                                  <IconButton size="small" component="a" href={meal.url} target="_blank" rel="noopener noreferrer">
                                    <LinkIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                              <IconButton size="small" onClick={() => startEdit(meal)}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton size="small" color="error" onClick={() => setDeleteId(meal.id)}>
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          }
                        >
                          <Chip
                            label={DAY_ABBR[meal.day_of_week]}
                            size="small"
                            variant="outlined"
                            sx={{ mr: 1.5, minWidth: 40, flexShrink: 0 }}
                          />
                          <ListItemText
                            primary={meal.name}
                            secondary={meal.notes
                              ? <Typography variant="body2" color="text.secondary" noWrap>{meal.notes}</Typography>
                              : null
                            }
                            primaryTypographyProps={{ fontWeight: 500 }}
                          />
                        </ListItem>
                        {meal.notes && (
                          <Collapse in={expandedMeals.has(meal.id)}>
                            <Box sx={{ px: 2, pb: 1.5, pt: 0.5 }}>
                              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                                {meal.notes}
                              </Typography>
                            </Box>
                          </Collapse>
                        )}
                      </Box>
                    )
                  )}
                </Box>
              )}

              {isCurrent && (
                <Box sx={{ mt: 1.5 }}>
                  {!showAdd ? (
                    <Button startIcon={<AddIcon />} size="small" variant="outlined" onClick={() => setShowAdd(true)}>
                      Add Meal
                    </Button>
                  ) : (
                    <Box component="form" onSubmit={handleAdd} sx={{ mt: 1 }}>
                      <Grid container spacing={1}>
                        <Grid item xs={12} sm={3}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Day</InputLabel>
                            <Select
                              value={addForm.day_of_week}
                              label="Day"
                              onChange={e => setAddForm(f => ({ ...f, day_of_week: e.target.value }))}
                            >
                              {DAYS.map((d, i) => <MenuItem key={d} value={i}>{d}</MenuItem>)}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid item xs={12} sm={9}>
                          <TextField
                            fullWidth size="small" label="Meal name" required
                            value={addForm.name}
                            onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
                            autoFocus
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth size="small" label="Notes (optional)"
                            value={addForm.notes}
                            onChange={e => setAddForm(f => ({ ...f, notes: e.target.value }))}
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth size="small" label="URL (optional)"
                            value={addForm.url}
                            onChange={e => setAddForm(f => ({ ...f, url: e.target.value }))}
                          />
                        </Grid>
                      </Grid>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <Button
                          type="submit" variant="contained" size="small"
                          disabled={submitting || !addForm.name.trim()}
                        >
                          Add
                        </Button>
                        <Button size="small" onClick={() => { setShowAdd(false); setAddForm(EMPTY_ADD) }}>
                          Cancel
                        </Button>
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        )
      })}

      <Dialog open={deleteId !== null} onClose={() => setDeleteId(null)}>
        <DialogTitle>Delete meal?</DialogTitle>
        <DialogContent>
          <Typography>{mealToDelete?.name}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
