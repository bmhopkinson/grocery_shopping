import { useState, useCallback } from 'react'

export function useMealPlanSession() {
  const [stage, setStage] = useState('cuisine_input')
  const [sessionId, setSessionId] = useState(null)
  const [statusMessages, setStatusMessages] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [mealOptions, setMealOptions] = useState(null)
  const [ingredients, setIngredients] = useState(null)
  const [remindersData, setRemindersData] = useState(null)
  const [completionData, setCompletionData] = useState(null)

  const addStatus = useCallback((message) => {
    setStatusMessages((prev) => [...prev, message])
  }, [])

  const processSSEStream = useCallback(async (response, onEvent) => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let eventType = null
    let dataLines = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        } else if (line === '' || line === '\r') {
          if (eventType && dataLines.length > 0) {
            try {
              const data = JSON.parse(dataLines.join(''))
              onEvent(eventType, data)
            } catch (e) {
              console.error('Failed to parse SSE data:', dataLines, e)
            }
          }
          eventType = null
          dataLines = []
        }
      }
    }
  }, [])

  const handleSSEEvent = useCallback((eventType, data) => {
    console.log('SSE Event:', eventType, data)

    switch (eventType) {
      case 'session_start':
        setSessionId(data.session_id)
        addStatus(`Session started: ${data.session_id}`)
        break
      case 'status':
        addStatus(data.message)
        break
      case 'meal_options':
        setMealOptions(data)
        setStage('meal_options')
        setLoading(false)
        break
      case 'ingredient_review':
        setIngredients(data)
        setStage('ingredient_review')
        setLoading(false)
        break
      case 'reminders_prompt':
        setRemindersData(data)
        setStage('reminders_prompt')
        setLoading(false)
        break
      case 'complete':
        setCompletionData(data)
        setStage('complete')
        setLoading(false)
        break
      case 'error':
        setError(data.message)
        setLoading(false)
        break
    }
  }, [addStatus])

  const startPlan = useCallback(async ({ cuisine, sources, directUrl }) => {
    setError(null)
    setLoading(true)
    setStatusMessages([])

    try {
      const body = directUrl
        ? { direct_url: directUrl }
        : { cuisine_type: cuisine, preferred_sources: sources }

      const response = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) throw new Error('Failed to start planning session')
      await processSSEStream(response, handleSSEEvent)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }, [processSSEStream, handleSSEEvent])

  const resumeSession = useCallback(async (input) => {
    if (!sessionId) return

    setError(null)
    setLoading(true)

    try {
      const response = await fetch(`/api/sessions/${sessionId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input }),
      })

      if (!response.ok) throw new Error('Failed to resume session')
      await processSSEStream(response, handleSSEEvent)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }, [sessionId, processSSEStream, handleSSEEvent])

  const reset = useCallback(() => {
    setStage('cuisine_input')
    setSessionId(null)
    setStatusMessages([])
    setError(null)
    setLoading(false)
    setMealOptions(null)
    setIngredients(null)
    setRemindersData(null)
    setCompletionData(null)
  }, [])

  return {
    stage,
    loading,
    error,
    setError,
    statusMessages,
    mealOptions,
    ingredients,
    remindersData,
    completionData,
    startPlan,
    resumeSession,
    reset,
  }
}
