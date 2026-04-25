import { Container, Paper, Stepper, Step, StepLabel, Box, Alert, Typography } from '@mui/material'
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
import WorkingListDetail from './components/WorkingListDetail'
import PageShell from './components/PageShell'
import BotanicalBanner from './components/BotanicalBanner'
import { useMealPlanSession } from './hooks/useMealPlanSession'
import { useState } from 'react'

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

export default function App() {
  const [mode, setMode] = useState('home')
  const [selectedWorkingList, setSelectedWorkingList] = useState(null)
  const {
    stage, loading, error, setError, statusMessages,
    mealOptions, ingredients, remindersData, completionData,
    startPlan, resumeSession, reset,
  } = useMealPlanSession()

  const goHome = () => { reset(); setMode('home'); setSelectedWorkingList(null) }

  if (mode === 'home') {
    return (
      <AppLayout>
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <HomeScreen onSelect={setMode} />
          </Paper>
        </Container>
      </AppLayout>
    )
  }

  if (mode === 'usuals') {
    return (
      <AppLayout>
        <PageShell onBack={goHome} header={<Typography variant="h6">Restock Usuals</Typography>}>
          <UsualsList />
        </PageShell>
      </AppLayout>
    )
  }

  if (mode === 'working_lists') {
    return (
      <AppLayout>
        <PageShell onBack={goHome} header={<Typography variant="h6">My Lists</Typography>}>
          {selectedWorkingList ? (
            <WorkingListDetail
              list={selectedWorkingList}
              onBack={() => setSelectedWorkingList(null)}
            />
          ) : (
            <WorkingLists onSelectList={setSelectedWorkingList} />
          )}
        </PageShell>
      </AppLayout>
    )
  }

  if (mode === 'reorder') {
    return (
      <AppLayout>
        <PageShell onBack={goHome} header={<Typography variant="h6">Organize List</Typography>}>
          <ReorderReminders />
        </PageShell>
      </AppLayout>
    )
  }

  if (mode === 'weekly_planner') {
    return (
      <AppLayout>
        <PageShell onBack={goHome} header={<Typography variant="h6">Weekly Planner</Typography>}>
          <WeeklyPlanner />
        </PageShell>
      </AppLayout>
    )
  }

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

        {stage === 'cuisine_input' && (
          <CuisineInput onSubmit={startPlan} loading={loading} />
        )}
        {stage === 'meal_options' && mealOptions && (
          <MealSelection data={mealOptions} onSelect={resumeSession} loading={loading} />
        )}
        {stage === 'ingredient_review' && ingredients && (
          <IngredientReview data={ingredients} onSubmit={resumeSession} loading={loading} />
        )}
        {stage === 'reminders_prompt' && remindersData && (
          <RemindersPrompt data={remindersData} onSubmit={resumeSession} loading={loading} />
        )}
        {stage === 'complete' && completionData && (
          <CompletionScreen data={completionData} onReset={reset} />
        )}
      </PageShell>
    </AppLayout>
  )
}
