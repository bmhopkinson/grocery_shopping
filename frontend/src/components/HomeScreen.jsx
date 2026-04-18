import { Box, Typography, Card, CardActionArea, CardContent, Grid } from '@mui/material'
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'

export default function HomeScreen({ onSelect }) {
  return (
    <Box sx={{ textAlign: 'center', py: 2 }}>
      <Typography variant="h4" gutterBottom>
        Grocery Shopping
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        What would you like to do?
      </Typography>
      <Grid container spacing={3} justifyContent="center">
        <Grid item xs={12} sm={5}>
          <Card elevation={2}>
            <CardActionArea onClick={() => onSelect('meal_plan')} sx={{ py: 3 }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <RestaurantMenuIcon sx={{ fontSize: 52, color: 'primary.main' }} />
                <Typography variant="h6">Plan Meals</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Search recipes and add ingredients to your shopping list
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item xs={12} sm={5}>
          <Card elevation={2}>
            <CardActionArea onClick={() => onSelect('usuals')} sx={{ py: 3 }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <ShoppingCartIcon sx={{ fontSize: 52, color: 'secondary.main' }} />
                <Typography variant="h6">Restock Usuals</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Add your regular breakfast, lunch, and snack items to Reminders
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
