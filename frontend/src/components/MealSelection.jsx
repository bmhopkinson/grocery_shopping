import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Chip,
  Link,
  RadioGroup,
  FormControlLabel,
  Radio,
} from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'

const getHostname = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return null
  }
}

export default function MealSelection({ data, onSelect, loading }) {
  const [selected, setSelected] = useState(null)
  const { options } = data

  const handleSubmit = () => {
    if (selected !== null) {
      onSelect(String(selected + 1))
    }
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
        Choose Your Recipe
      </Typography>

      <RadioGroup
        value={selected}
        onChange={(e) => setSelected(Number(e.target.value))}
      >
        <Grid container spacing={2}>
          {options.map((option, idx) => (
            <Grid item xs={12} key={idx}>
              <Card
                variant={selected === idx ? 'elevation' : 'outlined'}
                sx={{
                  cursor: 'pointer',
                  border: selected === idx ? 2 : 1,
                  borderColor: selected === idx ? 'primary.main' : 'divider',
                }}
                onClick={() => setSelected(idx)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                    <FormControlLabel
                      value={idx}
                      control={<Radio />}
                      label=""
                      sx={{ mr: 1, mt: -1 }}
                    />
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" gutterBottom>
                        {option.title}
                      </Typography>
                      {option.name && (
                        <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 500 }}>
                          {option.name}
                        </Typography>
                      )}
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {option.description}
                      </Typography>
                      {option.recipe_url && (
                        <Link
                          href={option.recipe_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, mb: 1 }}
                        >
                          View Recipe{getHostname(option.recipe_url) && ` (${getHostname(option.recipe_url)})`} <OpenInNewIcon fontSize="small" />
                        </Link>
                      )}
                      {option.cook_time && (
                        <Chip
                          label={`Cook time: ${option.cook_time}`}
                          size="small"
                          sx={{ mr: 1 }}
                        />
                      )}
                      {option.servings && (
                        <Chip
                          label={`Serves: ${option.servings}`}
                          size="small"
                        />
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </RadioGroup>

      <Box sx={{ mt: 3 }}>
        <Button
          variant="contained"
          fullWidth
          size="large"
          onClick={handleSubmit}
          disabled={selected === null || loading}
        >
          {loading ? 'Processing...' : 'Select This Recipe'}
        </Button>
      </Box>
    </Box>
  )
}
