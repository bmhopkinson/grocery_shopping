import { useState } from 'react'
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Button,
  TextField,
  Divider,
  Paper,
} from '@mui/material'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'

export default function IngredientReview({ data, onSubmit, loading }) {
  const { ingredients, instruction } = data
  const [checked, setChecked] = useState(
    ingredients.map((_, idx) => idx)
  )
  const [modifications, setModifications] = useState('')

  const handleToggle = (idx) => {
    setChecked((prev) =>
      prev.includes(idx)
        ? prev.filter((i) => i !== idx)
        : [...prev, idx].sort((a, b) => a - b)
    )
  }

  const handleSelectAll = () => {
    setChecked(ingredients.map((_, idx) => idx))
  }

  const handleSelectNone = () => {
    setChecked([])
  }

  const handleSubmit = () => {
    if (modifications.trim()) {
      onSubmit(modifications.trim())
    } else if (checked.length === ingredients.length) {
      onSubmit('yes')
    } else if (checked.length === 0) {
      onSubmit('remove all')
    } else {
      const removed = ingredients
        .filter((_, idx) => !checked.includes(idx))
        .map((ing) => ing.name)
      onSubmit(`remove: ${removed.join(', ')}`)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <ShoppingCartIcon color="primary" />
        <Typography variant="h5">Review Ingredients</Typography>
      </Box>

      {instruction && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {instruction}
        </Typography>
      )}

      <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
        <Button size="small" onClick={handleSelectAll}>
          Select All
        </Button>
        <Button size="small" onClick={handleSelectNone}>
          Clear All
        </Button>
      </Box>

      <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto', mb: 2 }}>
        <List dense>
          {ingredients.map((ingredient, idx) => (
            <ListItem
              key={idx}
              dense
              button
              onClick={() => handleToggle(idx)}
            >
              <ListItemIcon>
                <Checkbox
                  edge="start"
                  checked={checked.includes(idx)}
                  tabIndex={-1}
                  disableRipple
                />
              </ListItemIcon>
              <ListItemText
                primary={ingredient.name}
                secondary={`${ingredient.amount} ${ingredient.unit}`.trim()}
              />
            </ListItem>
          ))}
        </List>
      </Paper>

      <Divider sx={{ my: 2 }} />

      <TextField
        fullWidth
        label="Or type modifications"
        placeholder="e.g., 'remove garlic, add extra tomatoes'"
        value={modifications}
        onChange={(e) => setModifications(e.target.value)}
        multiline
        rows={2}
        sx={{ mb: 2 }}
      />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {checked.length} of {ingredients.length} ingredients selected
      </Typography>

      <Button
        variant="contained"
        fullWidth
        size="large"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? 'Processing...' : 'Confirm Ingredients'}
      </Button>
    </Box>
  )
}
