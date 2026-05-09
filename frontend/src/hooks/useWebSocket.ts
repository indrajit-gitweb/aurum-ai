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
  key_points?: string[]
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
  research_synthesis?: string
  aggressive_risk?: string
  aggressive_risk_signal?: string
  aggressive_risk_confidence?: number
  aggressive_risk_key_points?: string[]
  conservative_risk?: string
  conservative_risk_signal?: string
  conservative_risk_confidence?: number
  conservative_risk_key_points?: string[]
  neutral_risk?: string
  neutral_risk_signal?: string
  neutral_risk_confidence?: number
  neutral_risk_key_points?: string[]
}

export interface NewsItem {
  title: string
  date: string
  publisher: string
}

export interface InsiderTx {
  name: string
  role: string
  date: string
  type: string
  shares?: number
  value?: number
}

export interface TopHolder {
  name: string
  pct_held: string
}

export interface SecFiling {
  form: string        // "10-K" | "10-Q"
  filed_date: string  // "2024-11-01"
  report_date: string // "2024-09-28" (period end)
  url: string         // direct EDGAR filing index URL
}

export interface PeerData {
  ticker: string
  name: string
  price: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  ps_ratio: number | null
  profit_margin: number | null
  revenue_growth: number | null
  market_cap: number | null
  is_subject?: boolean   // true for the main ticker row
}

// DataSnapshot — raw fetched data from yfinance / SEC EDGAR / FRED
export interface DataSnapshot {
  company:               Record<string, unknown>
  valuation:             Record<string, unknown>
  profitability:         Record<string, unknown>
  financials:            Record<string, unknown>
  balance_sheet:         Record<string, unknown>
  cash_flow:             Record<string, unknown>
  growth:                Record<string, unknown>
  technical:             Record<string, unknown>
  market:                Record<string, unknown>
  macro:                 Record<string, unknown>
  analyst_recs:          Record<string, unknown>
  earnings:              Record<string, unknown>
  news:                  NewsItem[]
  insider_transactions:  InsiderTx[]
  top_holders:           TopHolder[]
  sec_filings:           SecFiling[]
  peer_comparison:       PeerData[]
}

interface UseWebSocketReturn {
  events: WSEvent[]
  isConnected: boolean
  isComplete: boolean
  finalResult: FinalResult | null
  dataSnapshot: DataSnapshot | null
  error: string | null
  stop: () => void
}

export function useWebSocket(sessionId: string | null): UseWebSocketReturn {
  const [events, setEvents] = useState<WSEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null)
  const [dataSnapshot, setDataSnapshot] = useState<DataSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  // Prevents reconnect when the server explicitly told us the session is gone
  const sessionLostRef = useRef(false)
  // BUG-15 fix: track isComplete via ref to avoid stale closure inside onclose
  const isCompleteRef = useRef(false)

  const stop = useCallback(() => {
    sessionLostRef.current = true   // prevent any reconnect
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current)
      reconnectRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

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

          // ── Raw data snapshot (emitted just before final_result) ────────────
          if (event.type === 'data_snapshot') {
            const { type: _t, timestamp: _ts, ...snap } = stamped as Record<string, unknown>
            setDataSnapshot(snap as unknown as DataSnapshot)
          }

          // ── Final result: data lives directly on the event, NOT under event.data ──
          if (event.type === 'final_result') {
            const { type: _t, timestamp: _ts, ...resultData } = stamped as Record<string, unknown>
            setFinalResult(resultData as unknown as FinalResult)
            isCompleteRef.current = true   // BUG-15 fix: update ref before state
            setIsComplete(true)
          }

          // ── Any server error: show banner and stop reconnecting ──────────
          if (event.type === 'error' && typeof event.message === 'string') {
            sessionLostRef.current = true   // stop reconnect loop
            if (
              event.message.includes('Session not found') ||
              event.message.includes('expired')
            ) {
              setError('Session expired — please start a new analysis.')
            } else {
              setError(event.message)
            }
          }
        } catch {
          // ignore JSON parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        // BUG-15 fix: use ref (not state) to avoid stale closure — isComplete state
        // is captured at closure creation time and never updates inside onclose.
        if (!isCompleteRef.current && !sessionLostRef.current && reconnectAttempts.current < 3) {
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
  }, [sessionId]) // BUG-13 fix: isComplete removed — isCompleteRef is used inside the closure instead

  useEffect(() => {
    if (!sessionId) return
    sessionLostRef.current = false   // reset on new session
    isCompleteRef.current = false    // BUG-15 fix: reset on new session
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

  return { events, isConnected, isComplete, finalResult, dataSnapshot, error, stop }
}
