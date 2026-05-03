import { Container, Paper, Stepper, Step, StepLabel, Box, Alert, Typography, CircularProgress } from '@mui/material'
import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import CuisineInput from './components/CuisineInput'
import MealSelection from './components/MealSelection'
import IngredientReview from './components/IngredientReview'
import RemindersPrompt from './components/RemindersPrompt'
import CompletionScreen from './components/CompletionScreen'
import StatusDisplay from './components/StatusDisplay'
import HomeScreen from './components/HomeScreen'
import UsualsList from './components/UsualsList'
import ReorderReminders from './components/ReorderReminders'
import WeeklyPlanner from './components/WeeklyPlanner'
import WorkingLists from './components/WorkingLists'
import RecipesList from './components/RecipesList'
import RecipeDetail from './components/RecipeDetail'
import WorkingListDetail from './components/WorkingListDetail'
import Management from './components/Management'
import PageShell from './components/PageShell'
import BotanicalBanner from './components/BotanicalBanner'
import { useMealPlanSession } from './hooks/useMealPlanSession'
import { useState, useEffect } from 'react'

const STEPS = ['Select Cuisine', 'Choose Recipe', 'Review Ingredients', 'Add to List']

const STAGE_TO_STEP = {
  cuisine_input: 0,
  meal_options: 1,
  ingredient_review: 2,
  reminders_prompt: 3,
  complete: 4,
}

function AppLayout({ children }) {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <BotanicalBanner />
      {children}
    </Box>
  )
}

function HomeRoute() {
  return (
    <AppLayout>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <HomeScreen />
        </Paper>
      </Container>
    </AppLayout>
  )
}

function MealPlanRoute() {
  const navigate = useNavigate()
  const {
    stage, loading, error, setError, statusMessages,
    mealOptions, ingredients, remindersData, completionData,
    startPlan, resumeSession, reset,
  } = useMealPlanSession()

  const goHome = () => { reset(); navigate('/') }
  const activeStep = STAGE_TO_STEP[stage] ?? 0

  return (
    <AppLayout>
      <PageShell
        onBack={goHome}
        header={
          <Stepper activeStep={activeStep} alternativeLabel>
            {STEPS.map(label => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
          </Stepper>
        }
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <StatusDisplay messages={statusMessages} loading={loading} />
        {stage === 'cuisine_input' && <CuisineInput onSubmit={startPlan} loading={loading} />}
        {stage === 'meal_options' && mealOptions && <MealSelection data={mealOptions} onSelect={resumeSession} loading={loading} />}
        {stage === 'ingredient_review' && ingredients && <IngredientReview data={ingredients} onSubmit={resumeSession} loading={loading} />}
        {stage === 'reminders_prompt' && remindersData && <RemindersPrompt data={remindersData} onSubmit={resumeSession} loading={loading} />}
        {stage === 'complete' && completionData && <CompletionScreen data={completionData} onReset={reset} />}
      </PageShell>
    </AppLayout>
  )
}

function UsualsRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">Restock Usuals</Typography>}>
        <UsualsList />
      </PageShell>
    </AppLayout>
  )
}

function ListsRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">My Lists</Typography>}>
        <WorkingLists onSelectList={list => navigate(`/lists/${list.id}`)} />
      </PageShell>
    </AppLayout>
  )
}

function ListDetailRoute() {
  const { listId } = useParams()
  const navigate = useNavigate()
  const [list, setList] = useState(null)

  useEffect(() => {
    fetch('/api/working-lists')
      .then(r => r.json())
      .then(lists => setList(lists.find(l => l.id === listId) ?? { id: listId, name: 'List' }))
      .catch(() => setList({ id: listId, name: 'List' }))
  }, [listId])

  if (!list) {
    return <AppLayout><Box sx={{ display: 'flex', justifyContent: 'center', p: 6 }}><CircularProgress /></Box></AppLayout>
  }

  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/lists')} header={<Typography variant="h6">{list.name}</Typography>}>
        <WorkingListDetail list={list} onBack={() => navigate('/lists')} />
      </PageShell>
    </AppLayout>
  )
}

function ReorderRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">Organize List</Typography>}>
        <ReorderReminders />
      </PageShell>
    </AppLayout>
  )
}

function WeeklyPlannerRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">Weekly Planner</Typography>}>
        <WeeklyPlanner />
      </PageShell>
    </AppLayout>
  )
}

function RecipesRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">Recipes</Typography>}>
        <RecipesList onSelectRecipe={recipe => navigate(`/recipes/${recipe.id}`)} />
      </PageShell>
    </AppLayout>
  )
}

function RecipeDetailRoute() {
  const { recipeId } = useParams()
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/recipes')} header={<Typography variant="h6">Recipe</Typography>}>
        <RecipeDetail recipeId={recipeId} />
      </PageShell>
    </AppLayout>
  )
}

function ManagementRoute() {
  const navigate = useNavigate()
  return (
    <AppLayout>
      <PageShell onBack={() => navigate('/')} header={<Typography variant="h6">Data Management</Typography>}>
        <Management />
      </PageShell>
    </AppLayout>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRoute />} />
      <Route path="/meal-plan" element={<MealPlanRoute />} />
      <Route path="/usuals" element={<UsualsRoute />} />
      <Route path="/lists" element={<ListsRoute />} />
      <Route path="/lists/:listId" element={<ListDetailRoute />} />
      <Route path="/reorder" element={<ReorderRoute />} />
      <Route path="/weekly-planner" element={<WeeklyPlannerRoute />} />
      <Route path="/recipes" element={<RecipesRoute />} />
      <Route path="/recipes/:recipeId" element={<RecipeDetailRoute />} />
      <Route path="/management" element={<ManagementRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
