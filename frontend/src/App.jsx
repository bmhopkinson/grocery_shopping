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
import PageShell from './components/PageShell'
import { useMealPlanSession } from './hooks/useMealPlanSession'
import { useState } from 'react'

const STEPS = ['Select Cuisine', 'Choose Recipe', 'Review Ingredients', 'Add to Reminders']

const STAGE_TO_STEP = {
  cuisine_input: 0,
  meal_options: 1,
  ingredient_review: 2,
  reminders_prompt: 3,
  complete: 4,
}

export default function App() {
  const [mode, setMode] = useState('home')
  const {
    stage, loading, error, setError, statusMessages,
    mealOptions, ingredients, remindersData, completionData,
    startPlan, resumeSession, reset,
  } = useMealPlanSession()

  const goHome = () => { reset(); setMode('home') }

  if (mode === 'home') {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <HomeScreen onSelect={setMode} />
        </Paper>
      </Container>
    )
  }

  if (mode === 'usuals') {
    return (
      <PageShell onBack={goHome} header={<Typography variant="h6">Restock Usuals</Typography>}>
        <UsualsList />
      </PageShell>
    )
  }

  if (mode === 'reorder') {
    return (
      <PageShell onBack={goHome} header={<Typography variant="h6">Organize List</Typography>}>
        <ReorderReminders />
      </PageShell>
    )
  }

  const activeStep = STAGE_TO_STEP[stage] ?? 0

  return (
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
  )
}
