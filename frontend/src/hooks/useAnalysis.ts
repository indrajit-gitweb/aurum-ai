import { useState, useCallback } from 'react'
import axios from 'axios'
import { BACKEND_URL, PersonaId, PERSONAS, WINDOW_MONTHS } from '@/lib/constants'
import type { AnalysisWindow, AnalysisMode } from '@/lib/constants'

interface ApiKeys {
  groq: string
  gemini: string
  openrouter: string
}

interface AnalysisForm {
  ticker: string
  analysisWindow: AnalysisWindow
  analysisMode: AnalysisMode
  customStartDate: string
  customEndDate: string
  selectedPersonas: PersonaId[]
  apiKeys: ApiKeys
}

interface UseAnalysisReturn {
  form: AnalysisForm
  isLoading: boolean
  error: string | null
  setTicker: (v: string) => void
  setAnalysisWindow: (w: AnalysisWindow) => void
  setAnalysisMode: (m: AnalysisMode) => void
  setCustomStartDate: (v: string) => void
  setCustomEndDate: (v: string) => void
  togglePersona: (id: PersonaId) => void
  setApiKey: (provider: keyof ApiKeys, value: string) => void
  selectAll: () => void
  selectCategory: (ids: PersonaId[]) => void
  resetToDefault: () => void
  startAnalysis: () => Promise<string | null>
  validate: () => string | null
}

/** Compute YYYY-MM-DD start/end dates from a window preset (or custom dates) */
function windowToDates(
  window: AnalysisWindow,
  customStart: string,
  customEnd: string,
): { startDate: string; endDate: string } {
  if (window === 'custom') {
    return { startDate: customStart, endDate: customEnd }
  }
  const today = new Date()
  const months = WINDOW_MONTHS[window as Exclude<AnalysisWindow, 'custom'>]
  const start = new Date(today.getFullYear(), today.getMonth() - months, today.getDate())
  return {
    startDate: start.toISOString().split('T')[0],
    endDate: today.toISOString().split('T')[0],
  }
}

export function useAnalysis(): UseAnalysisReturn {
  const [form, setForm] = useState<AnalysisForm>({
    ticker: '',
    analysisWindow: '1Y',
    analysisMode: 'current',
    customStartDate: '',
    customEndDate: '',
    selectedPersonas: [],
    apiKeys: { groq: '', gemini: '', openrouter: '' },
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setTicker = useCallback((v: string) => {
    setForm((f) => ({ ...f, ticker: v.toUpperCase().trim() }))
  }, [])

  const setAnalysisWindow = useCallback((w: AnalysisWindow) => {
    setForm((f) => ({ ...f, analysisWindow: w }))
  }, [])

  const setAnalysisMode = useCallback((m: AnalysisMode) => {
    setForm((f) => ({ ...f, analysisMode: m }))
  }, [])

  const setCustomStartDate = useCallback((v: string) => {
    setForm((f) => ({ ...f, customStartDate: v }))
  }, [])

  const setCustomEndDate = useCallback((v: string) => {
    setForm((f) => ({ ...f, customEndDate: v }))
  }, [])

  const togglePersona = useCallback((id: PersonaId) => {
    setForm((f) => ({
      ...f,
      selectedPersonas: f.selectedPersonas.includes(id)
        ? f.selectedPersonas.filter((p) => p !== id)
        : [...f.selectedPersonas, id],
    }))
  }, [])

  const setApiKey = useCallback((provider: keyof ApiKeys, value: string) => {
    setForm((f) => ({ ...f, apiKeys: { ...f.apiKeys, [provider]: value } }))
  }, [])

  const selectAll = useCallback(() => {
    setForm((f) => ({ ...f, selectedPersonas: PERSONAS.map((p) => p.id) as PersonaId[] }))
  }, [])

  const selectCategory = useCallback((ids: PersonaId[]) => {
    setForm((f) => ({
      ...f,
      selectedPersonas: Array.from(new Set([...f.selectedPersonas, ...ids])) as PersonaId[],
    }))
  }, [])

  const resetToDefault = useCallback(() => {
    setForm((f) => ({ ...f, selectedPersonas: [] }))
  }, [])

  const validate = useCallback((): string | null => {
    if (!form.ticker) return 'Please enter a stock ticker'
    if (form.ticker.length > 10) return 'Invalid ticker symbol'
    if (form.analysisWindow === 'custom') {
      if (!form.customStartDate || !form.customEndDate)
        return 'Please fill in both custom dates'
      if (new Date(form.customStartDate) >= new Date(form.customEndDate))
        return 'Start date must be before end date'
    }
    if (form.selectedPersonas.length === 0) return 'Please select at least one analyst'
    return null
  }, [form])

  const startAnalysis = useCallback(async (): Promise<string | null> => {
    const err = validate()
    if (err) {
      setError(err)
      return null
    }

    setIsLoading(true)
    setError(null)

    try {
      const { startDate, endDate } = windowToDates(
        form.analysisWindow,
        form.customStartDate,
        form.customEndDate,
      )
      const payload = {
        ticker: form.ticker,
        start_date: startDate,
        end_date: endDate,
        analysis_mode: form.analysisMode,
        personas: form.selectedPersonas,
        ...(form.apiKeys.groq       && { user_groq_key:       form.apiKeys.groq }),
        ...(form.apiKeys.gemini     && { user_gemini_key:     form.apiKeys.gemini }),
        ...(form.apiKeys.openrouter && { user_openrouter_key: form.apiKeys.openrouter }),
      }
      const res = await axios.post(`${BACKEND_URL}/api/analyze/start`, payload)
      const sessionId: string = res.data.session_id
      return sessionId
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e)
        ? e.response?.data?.detail || e.message
        : 'Failed to start analysis'
      setError(msg)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [form, validate])

  return {
    form,
    isLoading,
    error,
    setTicker,
    setAnalysisWindow,
    setAnalysisMode,
    setCustomStartDate,
    setCustomEndDate,
    togglePersona,
    setApiKey,
    selectAll,
    selectCategory,
    resetToDefault,
    startAnalysis,
    validate,
  }
}
