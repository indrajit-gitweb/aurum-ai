import { useState, useEffect, useRef, useCallback } from 'react'
import { BACKEND_URL } from '@/lib/constants'

// ── Backend event shape ───────────────────────────────────────────────────────
// The backend sends events with these exact field names.
// Fields are marked optional because different event types carry different data.
export interface WSEvent {
  type: string
  // Backend uses 'agent' (not 'agent_id') and 'message' (not 'content')
  agent?: string
  message?: string
  signal?: string       // lowercase from backend: 'bullish' | 'bearish' | 'neutral'
  confidence?: number
  reasoning?: string
  side?: string         // 'bull' | 'bear'  — for debate_message events
  // Final result fields live directly on the event (not nested under 'data')
  verdict?: string
  target_price?: number | null
  summary?: string
  bull_case?: string
  bear_case?: string
  risk_assessment?: string
  key_metrics?: Record<string, unknown>
  persona_signals?: FinalPersonaSignal[]
  // Legacy / fallback compatibility
  agent_id?: string
  agent_name?: string
  content?: string
  data?: Record<string, unknown>
  timestamp?: number
}

export interface FinalPersonaSignal {
  agent: string
  signal: string       // lowercase: 'bullish' | 'bearish' | 'neutral'
  confidence: number
  reasoning: string
}

// FinalResult matches exactly what the backend sends in the final_result event
export interface FinalResult {
  verdict: string
  confidence: number
  target_price?: number | null
  summary: string
  bull_case: string
  bear_case: string
  risk_assessment: string
  key_metrics: Record<string, unknown>
  persona_signals: FinalPersonaSignal[]
}

interface UseWebSocketReturn {
  events: WSEvent[]
  isConnected: boolean
  isComplete: boolean
  finalResult: FinalResult | null
  error: string | null
}

export function useWebSocket(sessionId: string | null): UseWebSocketReturn {
  const [events, setEvents] = useState<WSEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  // Prevents reconnect when the server explicitly told us the session is gone
  const sessionLostRef = useRef(false)

  const connect = useCallback(() => {
    if (!sessionId) return
    if (sessionLostRef.current) return   // don't reconnect after session-not-found

    const wsBase = BACKEND_URL.replace(/^http/, 'ws').replace(/\/$/, '')
    const wsUrl = `${wsBase}/ws/analyze/${sessionId}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (e) => {
        try {
          const event: WSEvent = JSON.parse(e.data)
          const stamped = { ...event, timestamp: Date.now() }
          setEvents((prev) => [...prev, stamped])

          // ── Final result: data lives directly on the event, NOT under event.data ──
          if (event.type === 'final_result') {
            const { type: _t, timestamp: _ts, ...resultData } = stamped as Record<string, unknown>
            setFinalResult(resultData as unknown as FinalResult)
            setIsComplete(true)
          }

          // ── Stop reconnecting if the session was already consumed ──
          if (
            event.type === 'error' &&
            typeof event.message === 'string' &&
            (event.message.includes('Session not found') || event.message.includes('expired'))
          ) {
            sessionLostRef.current = true
            setError('Session expired — please start a new analysis.')
          }
        } catch {
          // ignore JSON parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        // Only retry if: analysis didn't complete, session still valid, < 3 attempts
        if (!isComplete && !sessionLostRef.current && reconnectAttempts.current < 3) {
          reconnectAttempts.current += 1
          reconnectRef.current = setTimeout(connect, 2000 * reconnectAttempts.current)
        }
      }

      ws.onerror = () => {
        setError('Connection error — retrying...')
      }
    } catch {
      setError('Failed to connect to analysis server')
    }
  }, [sessionId, isComplete])

  useEffect(() => {
    if (!sessionId) return
    sessionLostRef.current = false   // reset on new session
    reconnectAttempts.current = 0
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current)
      }
    }
  }, [sessionId]) // only re-run when sessionId changes, not on connect reference change

  return { events, isConnected, isComplete, finalResult, error }
}
