import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, Circle, Loader, TrendingUp, TrendingDown, Minus, Download, RefreshCw } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PERSONAS } from '@/lib/constants'
import type { WSEvent } from '@/hooks/useWebSocket'
import type { FinalResult } from '@/hooks/useWebSocket'

// ─── Agent Status Map ──────────────────────────────────────────────────────────
type AgentStatus = 'pending' | 'running' | 'complete'

interface AgentState {
  id: string
  name: string
  initials: string
  status: AgentStatus
  signal?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  summary?: string
}

function buildInitialAgents(): AgentState[] {
  return PERSONAS.map((p) => ({
    id: p.id,
    name: p.name,
    initials: p.initials,
    status: 'pending',
  }))
}

// ─── Agent Timeline Item ───────────────────────────────────────────────────────
function AgentTimelineItem({ agent, isLast }: { agent: AgentState; isLast: boolean }) {
  const signalColors: Record<string, string> = {
    BULLISH: '#22c55e',
    BEARISH: '#ef4444',
    NEUTRAL: '#C0C0C0',
  }
  const signalIcons: Record<string, typeof TrendingUp> = {
    BULLISH: TrendingUp,
    BEARISH: TrendingDown,
    NEUTRAL: Minus,
  }

  return (
    <div className="relative flex gap-4 pb-6">
      {/* Vertical line */}
      {!isLast && (
        <div
          className="absolute left-5 top-10 bottom-0 w-px"
          style={{ background: 'rgba(255,255,255,0.07)' }}
        />
      )}

      {/* Icon */}
      <div className="relative shrink-0 mt-1">
        {agent.status === 'running' ? (
          <div className="relative">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-cinzel font-bold text-xs gold-pulse-ring"
              style={{
                background: 'rgba(201,168,76,0.15)',
                border: '1px solid rgba(201,168,76,0.6)',
                color: '#FFD700',
              }}
            >
              {agent.initials}
            </div>
            {/* Spinning ring */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="absolute -inset-1 rounded-full"
              style={{ border: '1px solid transparent', borderTopColor: '#C9A84C' }}
            />
          </div>
        ) : agent.status === 'complete' ? (
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-cinzel font-bold text-xs"
            style={{
              background: 'rgba(201,168,76,0.1)',
              border: '1px solid rgba(201,168,76,0.3)',
              color: '#C9A84C',
            }}
          >
            {agent.initials}
          </div>
        ) : (
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-cinzel font-bold text-xs"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.3)',
            }}
          >
            {agent.initials}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-0.5">
          <p
            className="font-cinzel text-sm font-semibold truncate"
            style={{
              color:
                agent.status === 'pending'
                  ? 'rgba(255,255,255,0.3)'
                  : agent.status === 'running'
                  ? '#ffffff'
                  : '#C9A84C',
            }}
          >
            {agent.name}
          </p>

          {agent.status === 'running' && (
            <span className="font-raleway text-xs ml-2 shrink-0 animate-pulse" style={{ color: '#C9A84C' }}>
              thinking…
            </span>
          )}

          {agent.status === 'complete' && agent.signal && (
            <span
              className="font-raleway text-xs font-semibold ml-2 shrink-0 px-2 py-0.5"
              style={{
                color: signalColors[agent.signal],
                background: `${signalColors[agent.signal]}18`,
                border: `1px solid ${signalColors[agent.signal]}40`,
              }}
            >
              {agent.signal === 'BULLISH' && <TrendingUp size={10} className="inline mr-1" />}
              {agent.signal === 'BEARISH' && <TrendingDown size={10} className="inline mr-1" />}
              {agent.signal === 'NEUTRAL' && <Minus size={10} className="inline mr-1" />}
              {agent.signal}
            </span>
          )}
        </div>

        {agent.status === 'complete' && agent.summary && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="font-raleway text-xs leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            {agent.summary}
          </motion.p>
        )}

        {agent.status === 'pending' && (
          <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>
            Queued
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Live Thought Stream ───────────────────────────────────────────────────────
interface ThoughtLine {
  agentName?: string
  content: string
  type: WSEvent['type']
  id: number
}

function ThoughtStream({ lines, isConnected }: { lines: ThoughtLine[]; isConnected: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines.length])

  const typeColor: Record<string, string> = {
    agent_thought: '#C9A84C',
    agent_start: '#FFD700',
    agent_complete: '#22c55e',
    debate_bull: '#22c55e',
    debate_bear: '#ef4444',
    error: '#ef4444',
    info: 'rgba(192,192,192,0.7)',
    final_result: '#FFD700',
  }

  return (
    <div
      className="h-full flex flex-col"
      style={{
        background: '#080808',
        border: '1px solid rgba(201,168,76,0.12)',
        fontFamily: "'Courier New', monospace",
      }}
    >
      {/* Terminal header */}
      <div
        className="flex items-center justify-between px-4 py-2 shrink-0"
        style={{ borderBottom: '1px solid rgba(201,168,76,0.1)' }}
      >
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ background: 'rgba(239,68,68,0.5)' }} />
            <div className="w-3 h-3 rounded-full" style={{ background: 'rgba(234,179,8,0.5)' }} />
            <div className="w-3 h-3 rounded-full" style={{ background: 'rgba(34,197,94,0.5)' }} />
          </div>
          <span className="font-raleway text-xs tracking-widest uppercase ml-2" style={{ color: 'rgba(201,168,76,0.5)' }}>
            Live Feed
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              background: isConnected ? '#22c55e' : '#ef4444',
              boxShadow: isConnected ? '0 0 6px #22c55e' : '0 0 6px #ef4444',
            }}
          />
          <span className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Scrollable log */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {lines.length === 0 && (
          <p style={{ color: 'rgba(201,168,76,0.3)' }} className="text-xs animate-pulse">
            {'>'} Awaiting analysis stream...
          </p>
        )}

        {lines.map((line) => (
          <motion.div
            key={line.id}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="text-xs leading-relaxed"
          >
            {line.agentName && (
              <span style={{ color: '#C9A84C', fontWeight: 'bold' }}>[{line.agentName}] </span>
            )}
            <span style={{ color: typeColor[line.type] || '#C0C0C0' }}>
              {line.type === 'agent_start' && '→ '}
              {line.type === 'agent_complete' && '✓ '}
              {line.content}
            </span>
          </motion.div>
        ))}

        {/* Blinking cursor */}
        {isConnected && (
          <div className="text-xs typing-cursor inline-block" style={{ color: '#C9A84C' }}>
            {' '}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ─── Debate Section ─────────────────────────────────────────────────────────────
function DebateSection({ bullLines, bearLines }: { bullLines: string[]; bearLines: string[] }) {
  if (bullLines.length === 0 && bearLines.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7 }}
      className="mt-6"
    >
      <h3 className="font-cinzel font-semibold text-white text-base mb-4 flex items-center gap-3">
        <span style={{ color: 'rgba(201,168,76,0.5)' }}>—</span>
        Bull vs Bear Debate
        <span style={{ color: 'rgba(201,168,76,0.5)' }}>—</span>
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Bull */}
        <div
          className="p-5"
          style={{ background: 'rgba(34,197,94,0.04)', border: '1px solid rgba(34,197,94,0.2)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} style={{ color: '#22c55e' }} />
            <span className="font-cinzel text-sm font-semibold" style={{ color: '#22c55e' }}>
              Bull Case
            </span>
          </div>
          <div className="space-y-2">
            {bullLines.map((line, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="font-raleway text-xs leading-relaxed"
                style={{ color: 'rgba(255,255,255,0.6)' }}
              >
                • {line}
              </motion.p>
            ))}
          </div>
        </div>

        {/* Bear */}
        <div
          className="p-5"
          style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.2)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown size={16} style={{ color: '#ef4444' }} />
            <span className="font-cinzel text-sm font-semibold" style={{ color: '#ef4444' }}>
              Bear Case
            </span>
          </div>
          <div className="space-y-2">
            {bearLines.map((line, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="font-raleway text-xs leading-relaxed"
                style={{ color: 'rgba(255,255,255,0.6)' }}
              >
                • {line}
              </motion.p>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Confidence Arc ────────────────────────────────────────────────────────────
function ConfidenceArc({ confidence }: { confidence: number }) {
  const radius = 60
  const circumference = Math.PI * radius
  const progress = (confidence / 100) * circumference

  return (
    <div className="relative flex flex-col items-center">
      <svg width="160" height="90" viewBox="0 0 160 90">
        {/* Track */}
        <path
          d="M 10 85 A 70 70 0 0 1 150 85"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        {/* Progress */}
        <motion.path
          d="M 10 85 A 70 70 0 0 1 150 85"
          fill="none"
          stroke="url(#goldGrad)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1.5, ease: 'easeOut', delay: 0.5 }}
        />
        <defs>
          <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#C9A84C" />
            <stop offset="50%" stopColor="#FFD700" />
            <stop offset="100%" stopColor="#C9A84C" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute bottom-0 text-center">
        <motion.p
          className="font-cinzel font-bold text-2xl"
          style={{ color: '#FFD700' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          {confidence}%
        </motion.p>
        <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Confidence
        </p>
      </div>
    </div>
  )
}

// ─── Final Result Banner ───────────────────────────────────────────────────────
function FinalResultBanner({ result, ticker }: { result: FinalResult; ticker: string }) {
  const navigate = useNavigate()
  const verdictConfig = {
    BUY: { color: '#C9A84C', glow: 'rgba(201,168,76,0.3)', label: 'BUY' },
    HOLD: { color: '#C0C0C0', glow: 'rgba(192,192,192,0.2)', label: 'HOLD' },
    SELL: { color: '#ef4444', glow: 'rgba(239,68,68,0.3)', label: 'SELL' },
  }
  const config = verdictConfig[result.verdict] || verdictConfig.HOLD

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="mt-8 relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #111111 0%, #0d0d0d 100%)',
        border: `1px solid ${config.color}40`,
        boxShadow: `0 0 60px ${config.glow}`,
      }}
    >
      {/* Particle burst background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {result.verdict === 'BUY' &&
          Array.from({ length: 12 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 rounded-full"
              style={{ background: '#FFD700', left: `${50 + (Math.random() - 0.5) * 80}%`, top: '50%' }}
              initial={{ scale: 0, opacity: 1 }}
              animate={{
                scale: [0, 1, 0],
                x: [(Math.random() - 0.5) * 200],
                y: [(Math.random() - 0.5) * 200],
                opacity: [1, 0.6, 0],
              }}
              transition={{ duration: 1.5, delay: i * 0.08 }}
            />
          ))}
      </div>

      <div className="relative z-10 p-8 md:p-12">
        {/* Verdict */}
        <div className="text-center mb-10">
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Consensus Verdict — {ticker}
          </p>
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6, type: 'spring', stiffness: 200, delay: 0.3 }}
          >
            <h2
              className="font-cinzel font-bold"
              style={{
                fontSize: 'clamp(4rem, 12vw, 9rem)',
                color: config.color,
                textShadow: `0 0 60px ${config.glow}, 0 0 120px ${config.glow}`,
                lineHeight: 1,
              }}
            >
              {config.label}
            </h2>
          </motion.div>
        </div>

        {/* Confidence + signals grid */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-10 mb-10">
          <ConfidenceArc confidence={result.confidence} />

          {/* Signal vote breakdown */}
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 max-w-sm">
            {Object.entries(result.agent_signals || {}).map(([agentId, data]) => {
              const persona = PERSONAS.find((p) => p.id === agentId)
              const sigColor = data.signal === 'BULLISH' ? '#22c55e' : data.signal === 'BEARISH' ? '#ef4444' : '#C0C0C0'
              return (
                <div
                  key={agentId}
                  className="flex flex-col items-center p-2"
                  style={{
                    background: `${sigColor}10`,
                    border: `1px solid ${sigColor}30`,
                  }}
                >
                  <span className="font-cinzel text-xs font-bold mb-1" style={{ color: sigColor }}>
                    {persona?.initials || agentId.slice(0, 2).toUpperCase()}
                  </span>
                  <span className="font-raleway" style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>
                    {data.signal === 'BULLISH' ? '▲' : data.signal === 'BEARISH' ? '▼' : '●'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Bull / Bear side by side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="p-6" style={{ background: 'rgba(34,197,94,0.04)', border: '1px solid rgba(34,197,94,0.15)' }}>
            <p className="font-cinzel text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: '#22c55e' }}>
              <TrendingUp size={14} /> Bull Case
            </p>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {result.bull_case}
            </p>
          </div>
          <div className="p-6" style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.15)' }}>
            <p className="font-cinzel text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: '#ef4444' }}>
              <TrendingDown size={14} /> Bear Case
            </p>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {result.bear_case}
            </p>
          </div>
        </div>

        {/* Risk + CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <span className="font-raleway text-xs tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Risk:{' '}
            </span>
            <span className="font-cinzel text-sm font-semibold" style={{ color: '#C9A84C' }}>
              {result.risk_rating || 'MODERATE'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <button
              className="flex items-center gap-2 font-raleway text-sm tracking-widest uppercase px-6 py-3 transition-all duration-300 hover:bg-gold/10"
              style={{ border: '1px solid rgba(201,168,76,0.3)', color: '#C9A84C' }}
              data-hover
            >
              <Download size={15} />
              Export PDF
            </button>
            <Link
              to="/analyser"
              className="flex items-center gap-2 font-raleway text-sm tracking-widest uppercase px-6 py-3 text-black transition-all duration-300"
              style={{ background: 'linear-gradient(135deg, #C9A84C, #FFD700)' }}
              data-hover
            >
              <RefreshCw size={15} />
              New Analysis
            </Link>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function LiveAnalysisPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { events, isConnected, isComplete, finalResult, error: wsError } = useWebSocket(sessionId || null)

  const [agents, setAgents] = useState<AgentState[]>(buildInitialAgents())
  const [thoughtLines, setThoughtLines] = useState<ThoughtLine[]>([])
  const [bullLines, setBullLines] = useState<string[]>([])
  const [bearLines, setBearLines] = useState<string[]>([])
  const [ticker, setTicker] = useState<string>(sessionId?.split('-')[0]?.toUpperCase() || 'STOCK')
  const timelineBottomRef = useRef<HTMLDivElement>(null)
  const lineCounter = useRef(0)

  // Process incoming WebSocket events
  useEffect(() => {
    const latest = events[events.length - 1]
    if (!latest) return

    const newLine: ThoughtLine = {
      agentName: latest.agent_name,
      content: latest.content || JSON.stringify(latest.data || ''),
      type: latest.type,
      id: lineCounter.current++,
    }
    setThoughtLines((prev) => [...prev.slice(-300), newLine])

    switch (latest.type) {
      case 'agent_start':
        setAgents((prev) =>
          prev.map((a) =>
            a.id === latest.agent_id ? { ...a, status: 'running' } : a
          )
        )
        break
      case 'agent_complete':
        setAgents((prev) =>
          prev.map((a) =>
            a.id === latest.agent_id
              ? { ...a, status: 'complete', signal: latest.signal, summary: latest.summary }
              : a
          )
        )
        timelineBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
        break
      case 'debate_bull':
        if (latest.content) setBullLines((prev) => [...prev, latest.content!])
        break
      case 'debate_bear':
        if (latest.content) setBearLines((prev) => [...prev, latest.content!])
        break
    }

    if (latest.agent_id) {
      setTicker(latest.agent_id.includes('-') ? ticker : ticker)
    }
  }, [events.length]) // eslint-disable-line

  const completedCount = agents.filter((a) => a.status === 'complete').length
  const totalAgents = agents.filter((a) => a.status !== 'pending' || completedCount > 0).length || PERSONAS.length

  return (
    <div className="min-h-screen pt-20 pb-16" style={{ background: '#0a0a0a' }}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="pt-8 pb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-1" style={{ color: 'rgba(201,168,76,0.6)' }}>
                Live Analysis
              </p>
              <h1 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)' }}>
                {ticker}
              </h1>
            </div>

            {/* Progress / status */}
            <div className="flex items-center gap-4">
              {!isComplete && (
                <div className="flex items-center gap-3">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    style={{ color: '#C9A84C' }}
                  >
                    <Loader size={18} />
                  </motion.div>
                  <div>
                    <p className="font-raleway text-xs font-medium" style={{ color: '#C9A84C' }}>
                      Analysis in progress
                    </p>
                    <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {completedCount} / {PERSONAS.length} analysts complete
                    </p>
                  </div>
                </div>
              )}
              {isComplete && (
                <div className="flex items-center gap-2">
                  <CheckCircle size={18} style={{ color: '#22c55e' }} />
                  <p className="font-raleway text-sm font-medium" style={{ color: '#22c55e' }}>
                    Analysis Complete
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-4 h-px w-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <motion.div
              className="h-full"
              style={{
                background: 'linear-gradient(90deg, #C9A84C, #FFD700)',
                boxShadow: '0 0 8px rgba(201,168,76,0.4)',
              }}
              animate={{ width: `${(completedCount / PERSONAS.length) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {wsError && (
          <div
            className="mb-6 px-5 py-4 font-raleway text-sm"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}
          >
            {wsError}
          </div>
        )}

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6" style={{ minHeight: '65vh' }}>
          {/* Left — Agent Timeline (40%) */}
          <div className="lg:col-span-2 overflow-y-auto" style={{ maxHeight: '70vh' }}>
            <div
              className="p-5"
              style={{ background: '#0d0d0d', border: '1px solid rgba(201,168,76,0.1)' }}
            >
              <p className="font-cinzel text-xs font-semibold tracking-widest uppercase mb-6" style={{ color: 'rgba(201,168,76,0.6)' }}>
                Analyst Progress
              </p>
              {agents.map((agent, i) => (
                <AgentTimelineItem key={agent.id} agent={agent} isLast={i === agents.length - 1} />
              ))}
              <div ref={timelineBottomRef} />
            </div>
          </div>

          {/* Right — Thought Stream (60%) */}
          <div className="lg:col-span-3" style={{ minHeight: '400px' }}>
            <ThoughtStream lines={thoughtLines} isConnected={isConnected} />
          </div>
        </div>

        {/* Debate Section */}
        <AnimatePresence>
          {(bullLines.length > 0 || bearLines.length > 0) && (
            <DebateSection bullLines={bullLines} bearLines={bearLines} />
          )}
        </AnimatePresence>

        {/* Final Result */}
        <AnimatePresence>
          {isComplete && finalResult && (
            <FinalResultBanner result={finalResult} ticker={ticker} />
          )}
        </AnimatePresence>

        {/* Demo mode when no ws connection yet */}
        {thoughtLines.length === 0 && !isConnected && (
          <div className="mt-8 text-center py-16">
            <motion.div
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="font-raleway text-sm"
              style={{ color: 'rgba(201,168,76,0.5)' }}
            >
              Connecting to analysis engine...
            </motion.div>
            <p className="font-raleway text-xs mt-2" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Session: {sessionId}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
