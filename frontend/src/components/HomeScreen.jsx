import { Box, Typography, Card, CardActionArea, CardContent, Grid, Chip } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import ListAltIcon from '@mui/icons-material/ListAlt'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import MenuBookIcon from '@mui/icons-material/MenuBook'

function NavCard({ onClick, icon, title, description }) {
  return (
    <Card elevation={2} sx={{ height: 200 }}>
      <CardActionArea onClick={onClick} sx={{ py: 3, height: '100%' }}>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5 }}>
          {icon}
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary" align="center">{description}</Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  )
}

function SectionHeader({ label }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2.5 }}>
      <Chip label={label} size="small" sx={{ fontWeight: 500, letterSpacing: 0.5 }} />
    </Box>
  )
}

export default function HomeScreen() {
  const navigate = useNavigate()
  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="h4" gutterBottom align="center">
        Grocery Shopping
      </Typography>

      <Box sx={{ mt: 4, mb: 2 }}>
        <SectionHeader label="Plan & Shop" />
        <Grid container spacing={3} justifyContent="center">
          <Grid item xs={12} sm={4}>
            <NavCard
              onClick={() => navigate('/meal-plan')}
              icon={<RestaurantMenuIcon sx={{ fontSize: 52, color: 'primary.main' }} />}
              title="Plan Meals"
              description="Search recipes and add ingredients to your shopping list"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <NavCard
              onClick={() => navigate('/usuals')}
              icon={<ShoppingCartIcon sx={{ fontSize: 52, color: 'secondary.main' }} />}
              title="Restock Usuals"
              description="Add your regular items to a shopping list"
            />
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ mt: 4 }}>
        <SectionHeader label="My Kitchen" />
        <Grid container spacing={3} justifyContent="center">
          <Grid item xs={12} sm={4}>
            <NavCard
              onClick={() => navigate('/recipes')}
              icon={<MenuBookIcon sx={{ fontSize: 52, color: 'success.main' }} />}
              title="Recipes"
              description="Save and manage your favorite recipes"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <NavCard
              onClick={() => navigate('/lists')}
              icon={<ListAltIcon sx={{ fontSize: 52, color: 'info.main' }} />}
              title="My Lists"
              description="Manage shopping lists, organize by store, send to Reminders"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <NavCard
              onClick={() => navigate('/weekly-planner')}
              icon={<CalendarMonthIcon sx={{ fontSize: 52, color: 'warning.main' }} />}
              title="Weekly Planner"
              description="Plan meals for each day of the week"
            />
          </Grid>
        </Grid>
      </Box>
    </Box>
  )
}
