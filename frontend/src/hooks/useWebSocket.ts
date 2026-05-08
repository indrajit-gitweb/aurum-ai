import { useState, useEffect, useRef, useCallback } from 'react'
import { BACKEND_URL } from '@/lib/constants'

export interface WSEvent {
  type: 'agent_start' | 'agent_thought' | 'agent_complete' | 'debate_bull' | 'debate_bear' | 'final_result' | 'error' | 'info'
  agent_id?: string
  agent_name?: string
  content?: string
  signal?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  summary?: string
  data?: Record<string, unknown>
  timestamp?: number
}

export interface FinalResult {
  verdict: 'BUY' | 'HOLD' | 'SELL'
  confidence: number
  bull_case: string
  bear_case: string
  risk_rating: string
  agent_signals: Record<string, { signal: string; summary: string }>
  executive_summary: string
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

  const connect = useCallback(() => {
    if (!sessionId) return

    const wsUrl = BACKEND_URL.replace('http', 'ws') + `/ws/${sessionId}`

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
          setEvents((prev) => [...prev, { ...event, timestamp: Date.now() }])

          if (event.type === 'final_result' && event.data) {
            setFinalResult(event.data as unknown as FinalResult)
            setIsComplete(true)
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (!isComplete && reconnectAttempts.current < 3) {
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
  }, [sessionId, connect])

  return { events, isConnected, isComplete, finalResult, error }
}
