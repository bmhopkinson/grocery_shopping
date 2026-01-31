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

export default function CompletionScreen({ data, onReset }) {
  const { selected_meal, grocery_list, reminders_added } = data

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
            <Typography variant="h6" gutterBottom>
              Selected Recipe
            </Typography>
            <Typography variant="h5" color="primary.main" gutterBottom>
              {selected_meal.title}
            </Typography>
            {selected_meal.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {selected_meal.description}
              </Typography>
            )}
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {selected_meal.cook_time && (
                <Chip label={`Cook time: ${selected_meal.cook_time}`} size="small" />
              )}
              {selected_meal.servings && (
                <Chip label={`Serves: ${selected_meal.servings}`} size="small" />
              )}
            </Box>
            {selected_meal.url && (
              <Box sx={{ mt: 2 }}>
                <Link
                  href={selected_meal.url}
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
                  secondary={
                    [item.quantity, item.unit, item.notes]
                      .filter(Boolean)
                      .join(' ')
                  }
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
        Plan Another Meal
      </Button>
    </Box>
  )
}
