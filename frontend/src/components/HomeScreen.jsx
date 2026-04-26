import { Box, Typography, Card, CardActionArea, CardContent, Grid } from '@mui/material'
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import ListAltIcon from '@mui/icons-material/ListAlt'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import MenuBookIcon from '@mui/icons-material/MenuBook'

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
        <Grid item xs={12} sm={4}>
          <Card elevation={2} sx={{ height: 230 }}>
            <CardActionArea onClick={() => onSelect('meal_plan')} sx={{ py: 3, height: '100%' }}>
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
        <Grid item xs={12} sm={4}>
          <Card elevation={2} sx={{ height: 230 }}>
            <CardActionArea onClick={() => onSelect('usuals')} sx={{ py: 3, height: '100%' }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <ShoppingCartIcon sx={{ fontSize: 52, color: 'secondary.main' }} />
                <Typography variant="h6">Restock Usuals</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Add your regular items to a shopping list
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card elevation={2} sx={{ height: 230 }}>
            <CardActionArea onClick={() => onSelect('working_lists')} sx={{ py: 3, height: '100%' }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <ListAltIcon sx={{ fontSize: 52, color: 'info.main' }} />
                <Typography variant="h6">My Lists</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Manage shopping lists, organize by store, send to Reminders
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card elevation={2} sx={{ height: 230 }}>
            <CardActionArea onClick={() => onSelect('weekly_planner')} sx={{ py: 3, height: '100%' }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <CalendarMonthIcon sx={{ fontSize: 52, color: 'warning.main' }} />
                <Typography variant="h6">Weekly Planner</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Plan meals for each day of the week
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card elevation={2} sx={{ height: 230 }}>
            <CardActionArea onClick={() => onSelect('recipes')} sx={{ py: 3, height: '100%' }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
                <MenuBookIcon sx={{ fontSize: 52, color: 'success.main' }} />
                <Typography variant="h6">Recipes</Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  Save and manage your favorite recipes
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
