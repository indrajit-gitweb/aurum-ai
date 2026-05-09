import { useState, useCallback } from 'react'
import axios from 'axios'
import { BACKEND_URL, PersonaId } from '@/lib/constants'

interface ApiKeys {
  groq: string
  gemini: string
  openrouter: string
}

interface AnalysisForm {
  ticker: string
  startDate: string
  endDate: string
  selectedPersonas: PersonaId[]
  apiKeys: ApiKeys
}

interface UseAnalysisReturn {
  form: AnalysisForm
  isLoading: boolean
  error: string | null
  setTicker: (v: string) => void
  setStartDate: (v: string) => void
  setEndDate: (v: string) => void
  togglePersona: (id: PersonaId) => void
  setApiKey: (provider: keyof ApiKeys, value: string) => void
  selectAll: () => void
  selectCategory: (ids: PersonaId[]) => void
  resetToDefault: () => void
  startAnalysis: () => Promise<string | null>
  validate: () => string | null
}

const today = new Date().toISOString().split('T')[0]
const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

import { PERSONAS } from '@/lib/constants'

export function useAnalysis(): UseAnalysisReturn {
  const [form, setForm] = useState<AnalysisForm>({
    ticker: '',
    startDate: oneYearAgo,
    endDate: today,
    selectedPersonas: [],   // start empty — user picks from category tabs
    apiKeys: { groq: '', gemini: '', openrouter: '' },
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setTicker = useCallback((v: string) => {
    setForm((f) => ({ ...f, ticker: v.toUpperCase().trim() }))
  }, [])

  const setStartDate = useCallback((v: string) => {
    setForm((f) => ({ ...f, startDate: v }))
  }, [])

  const setEndDate = useCallback((v: string) => {
    setForm((f) => ({ ...f, endDate: v }))
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

  // Add all personas in a category to the selection without deselecting others
  const selectCategory = useCallback((ids: PersonaId[]) => {
    setForm((f) => ({
      ...f,
      selectedPersonas: Array.from(new Set([...f.selectedPersonas, ...ids])) as PersonaId[],
    }))
  }, [])

  const resetToDefault = useCallback(() => {
    setForm((f) => ({ ...f, selectedPersonas: [] }))  // clear all — user picks from categories
  }, [])

  const validate = useCallback((): string | null => {
    if (!form.ticker) return 'Please enter a stock ticker'
    if (form.ticker.length > 10) return 'Invalid ticker symbol'
    if (!form.startDate || !form.endDate) return 'Please select a date range'
    if (new Date(form.startDate) >= new Date(form.endDate)) return 'Start date must be before end date'
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
      const payload = {
        ticker: form.ticker,
        start_date: form.startDate,
        end_date: form.endDate,
        personas: form.selectedPersonas,
        ...(form.apiKeys.groq      && { user_groq_key:       form.apiKeys.groq }),
        ...(form.apiKeys.gemini    && { user_gemini_key:     form.apiKeys.gemini }),
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
    setStartDate,
    setEndDate,
    togglePersona,
    setApiKey,
    selectAll,
    selectCategory,
    resetToDefault,
    startAnalysis,
    validate,
  }
}
