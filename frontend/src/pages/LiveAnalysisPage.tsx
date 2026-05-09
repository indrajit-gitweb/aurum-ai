import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, Loader, TrendingUp, TrendingDown, Minus, Download, RefreshCw, AlertCircle, ChevronsDown, Square, ChevronDown, Database } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PERSONAS, VERDICT_CONFIG } from '@/lib/constants'
import type { WSEvent, FinalResult, DataSnapshot } from '@/hooks/useWebSocket'

// ─── Agent Status ──────────────────────────────────────────────────────────────
type AgentStatus = 'pending' | 'running' | 'complete'

// Consistent label for unselected personas
const NOT_SELECTED_LABEL = 'On Leave'

// ─── Pipeline Step Tracking ────────────────────────────────────────────────────
type PipelineStatus = 'pending' | 'running' | 'complete'

interface PipelineStep {
  id: string
  label: string
  status: PipelineStatus
}

const PIPELINE_STEP_DEFS: readonly { id: string; label: string }[] = [
  { id: 'data_fetcher',         label: 'Price Data'   },
  { id: 'fundamentals_analyst', label: 'Fundamentals' },
  { id: 'technical_analyst',    label: 'Technicals'   },
  { id: 'news_analyst',         label: 'News'         },
  { id: 'macro_analyst',        label: 'Macro'        },
  { id: 'debate_bull',          label: 'Bull Case'    },
  { id: 'debate_bear',          label: 'Bear Case'    },
  { id: 'research_manager',     label: 'Research'     },
  { id: 'portfolio_manager',    label: 'Verdict'      },
]

const PIPELINE_AGENT_IDS = new Set(PIPELINE_STEP_DEFS.map((s) => s.id))

interface AgentState {
  id: string
  name: string
  initials: string
  status: AgentStatus
  isSelected: boolean          // was this persona chosen for this run?
  notSelectedLabel: string     // fun label when not selected
  signal?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  summary?: string
}

// ─── Helpers ───────────────────────────────────────────────────────────────────
/** Normalize the 'agent' field from a WSEvent — backend sends 'agent', not 'agent_id' */
function getAgentId(ev: WSEvent): string {
  return ev.agent || ev.agent_id || ''
}

/** Get displayable text from a WSEvent — backend sends 'message', not 'content' */
function getEventText(ev: WSEvent): string {
  return ev.message || ev.content || ev.reasoning || ''
}

/** Convert lowercase backend signal to uppercase UI signal */
function normalizeSignal(raw?: string): 'BULLISH' | 'BEARISH' | 'NEUTRAL' {
  const up = (raw || '').toUpperCase()
  if (up === 'BULLISH') return 'BULLISH'
  if (up === 'BEARISH') return 'BEARISH'
  return 'NEUTRAL'
}

/** Look up a human-readable agent name from the personas list or format the id */
function getAgentName(agentId: string, eventAgentName?: string): string {
  if (eventAgentName) return eventAgentName
  const p = PERSONAS.find((p) => p.id === agentId)
  if (p) return p.name
  // Format snake_case ids nicely
  return agentId.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// ─── Agent Timeline Item ───────────────────────────────────────────────────────
function AgentTimelineItem({ agent, isLast }: { agent: AgentState; isLast: boolean }) {
  const signalColors = { BULLISH: '#22c55e', BEARISH: '#ef4444', NEUTRAL: '#C0C0C0' }

  return (
    <div className="relative flex gap-4 pb-6">
      {!isLast && (
        <div className="absolute left-5 top-10 bottom-0 w-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
      )}

      <div className="relative shrink-0 mt-1">
        {agent.status === 'running' ? (
          <div className="relative">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-cinzel font-bold text-xs"
              style={{ background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.6)', color: '#FFD700' }}
            >
              {agent.initials}
            </div>
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
            style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.3)', color: '#C9A84C' }}
          >
            {agent.initials}
          </div>
        ) : (
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center font-cinzel font-bold text-xs"
            style={{
              background: agent.isSelected ? 'rgba(255,255,255,0.03)' : 'transparent',
              border: agent.isSelected ? '1px solid rgba(255,255,255,0.08)' : '1px dashed rgba(255,255,255,0.06)',
              color: agent.isSelected ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.12)',
            }}
          >
            {agent.initials}
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-0.5">
          <p
            className="font-cinzel text-sm font-semibold truncate"
            style={{
              color: agent.status === 'pending' ? 'rgba(255,255,255,0.3)' : agent.status === 'running' ? '#ffffff' : '#C9A84C',
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
            {agent.summary.slice(0, 120)}{agent.summary.length > 120 ? '…' : ''}
          </motion.p>
        )}
        {agent.status === 'pending' && agent.isSelected && (
          <p className="font-raleway text-xs" style={{ color: 'rgba(201,168,76,0.35)' }}>Awaiting turn…</p>
        )}
        {agent.status === 'pending' && !agent.isSelected && (
          <p className="font-raleway text-xs italic" style={{ color: 'rgba(255,255,255,0.15)' }}>
            {agent.notSelectedLabel}
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
  type: string
  id: number
}

function ThoughtStream({ lines, isConnected }: { lines: ThoughtLine[]; isConnected: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [showScrollBtn, setShowScrollBtn] = useState(false)

  // Auto-scroll to bottom when new lines arrive (only if autoScroll is on)
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines.length, autoScroll])

  // Detect when user scrolls up — disable auto-scroll and show jump button
  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    const userScrolledUp = distanceFromBottom > 80
    setAutoScroll(!userScrolledUp)
    setShowScrollBtn(userScrolledUp)
  }

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    setAutoScroll(true)
    setShowScrollBtn(false)
  }

  const typeColor: Record<string, string> = {
    agent_start:    '#FFD700',
    agent_progress: '#C9A84C',
    agent_thought:  '#C9A84C',
    agent_complete: '#22c55e',
    debate_start:   'rgba(201,168,76,0.5)',
    debate_message: '#C9A84C',
    debate_bull:    '#22c55e',
    debate_bear:    '#ef4444',
    error:          '#ef4444',
    info:           'rgba(192,192,192,0.7)',
    final_result:   '#FFD700',
  }

  return (
    <div
      className="h-full flex flex-col relative"
      style={{ background: '#080808', border: '1px solid rgba(201,168,76,0.12)', fontFamily: "'Courier New', monospace" }}
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
        <div className="flex items-center gap-3">
          {/* Scroll-to-bottom hint when auto-scroll is off */}
          {showScrollBtn && (
            <button
              onClick={scrollToBottom}
              className="flex items-center gap-1 font-raleway text-xs px-2 py-0.5 transition-all duration-200"
              style={{ color: '#C9A84C', border: '1px solid rgba(201,168,76,0.3)', background: 'rgba(201,168,76,0.08)' }}
            >
              <ChevronsDown size={11} />
              Latest
            </button>
          )}
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: isConnected ? '#22c55e' : '#ef4444', boxShadow: isConnected ? '0 0 6px #22c55e' : '0 0 6px #ef4444' }}
            />
            <span className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Scrollable log */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-1"
      >
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
              {line.type === 'debate_start' && '⚔ '}
              {line.content}
            </span>
          </motion.div>
        ))}

        {isConnected && (
          <div className="text-xs inline-block animate-pulse" style={{ color: '#C9A84C' }}>▌</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ─── Pipeline Steps Bar ────────────────────────────────────────────────────────
function PipelineStepsBar({ steps }: { steps: PipelineStep[] }) {
  return (
    <div
      className="flex flex-wrap gap-1.5 px-5 py-3 mb-0"
      style={{ background: '#0a0a0a', borderBottom: '1px solid rgba(201,168,76,0.08)' }}
    >
      {steps.map((step) => {
        const isDone    = step.status === 'complete'
        const isRunning = step.status === 'running'
        return (
          <div
            key={step.id}
            className="flex items-center gap-1 px-2 py-0.5 font-raleway text-xs"
            style={{
              border: isDone
                ? '1px solid rgba(34,197,94,0.35)'
                : isRunning
                ? '1px solid rgba(201,168,76,0.5)'
                : '1px solid rgba(255,255,255,0.06)',
              background: isDone
                ? 'rgba(34,197,94,0.06)'
                : isRunning
                ? 'rgba(201,168,76,0.08)'
                : 'transparent',
              color: isDone ? '#22c55e' : isRunning ? '#C9A84C' : 'rgba(255,255,255,0.2)',
            }}
          >
            {isRunning && (
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{ display: 'inline-block', width: 5, height: 5, borderRadius: '50%', background: '#C9A84C', flexShrink: 0 }}
              />
            )}
            {isDone && <span style={{ fontSize: 9 }}>✓</span>}
            {step.status === 'pending' && (
              <span style={{ display: 'inline-block', width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />
            )}
            <span>{step.label}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─── Debate Section ────────────────────────────────────────────────────────────
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
        <div className="p-5" style={{ background: 'rgba(34,197,94,0.04)', border: '1px solid rgba(34,197,94,0.2)' }}>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} style={{ color: '#22c55e' }} />
            <span className="font-cinzel text-sm font-semibold" style={{ color: '#22c55e' }}>Bull Case</span>
          </div>
          <div className="space-y-2">
            {bullLines.map((line, i) => (
              <motion.p key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                className="font-raleway text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {line}
              </motion.p>
            ))}
          </div>
        </div>
        <div className="p-5" style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown size={16} style={{ color: '#ef4444' }} />
            <span className="font-cinzel text-sm font-semibold" style={{ color: '#ef4444' }}>Bear Case</span>
          </div>
          <div className="space-y-2">
            {bearLines.map((line, i) => (
              <motion.p key={i} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                className="font-raleway text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {line}
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
        <path d="M 10 85 A 70 70 0 0 1 150 85" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" strokeLinecap="round" />
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
        <motion.p className="font-cinzel font-bold text-2xl" style={{ color: '#FFD700' }}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
          {confidence}%
        </motion.p>
        <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Confidence</p>
      </div>
    </div>
  )
}

// ─── Final Result Banner ───────────────────────────────────────────────────────
function FinalResultBanner({ result, ticker, onExportPDF }: { result: FinalResult; ticker: string; onExportPDF: () => void }) {
  // Normalise verdict — backend can send "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
  const verdictKey = result.verdict?.toUpperCase() as keyof typeof VERDICT_CONFIG
  const config = VERDICT_CONFIG[verdictKey] || VERDICT_CONFIG['HOLD']

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
                fontSize: 'clamp(3rem, 10vw, 7rem)',
                color: config.color,
                textShadow: `0 0 60px ${config.glow}, 0 0 120px ${config.glow}`,
                lineHeight: 1,
              }}
            >
              {config.label}
            </h2>
          </motion.div>
          {result.target_price && (
            <p className="font-raleway text-sm mt-3" style={{ color: 'rgba(255,255,255,0.5)' }}>
              Target Price:{' '}
              <span className="font-cinzel font-semibold" style={{ color: '#C9A84C' }}>
                ${result.target_price.toFixed(2)}
              </span>
            </p>
          )}
        </div>

        {/* Confidence + persona signal bubbles */}
        <div className="flex flex-col md:flex-row items-center justify-center gap-10 mb-10">
          <ConfidenceArc confidence={result.confidence} />

          {/* Persona signal grid — backend sends persona_signals as an array */}
          <div className="grid grid-cols-4 sm:grid-cols-5 gap-2 max-w-xs">
            {(result.persona_signals || []).map((sig) => {
              const persona = PERSONAS.find((p) => p.id === sig.agent)
              const sigUp = (sig.signal || '').toUpperCase()
              const sigColor = sigUp === 'BULLISH' ? '#22c55e' : sigUp === 'BEARISH' ? '#ef4444' : '#C0C0C0'
              return (
                <div
                  key={sig.agent}
                  className="flex flex-col items-center p-2"
                  title={`${persona?.name || sig.agent}: ${sig.signal} (${sig.confidence}%)`}
                  style={{ background: `${sigColor}10`, border: `1px solid ${sigColor}30` }}
                >
                  <span className="font-cinzel text-xs font-bold mb-1" style={{ color: sigColor }}>
                    {persona?.initials || sig.agent.slice(0, 2).toUpperCase()}
                  </span>
                  <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)' }}>
                    {sigUp === 'BULLISH' ? '▲' : sigUp === 'BEARISH' ? '▼' : '●'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Executive summary */}
        {result.summary && (
          <div className="mb-8 p-5 text-center" style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.12)' }}>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>
              {result.summary}
            </p>
          </div>
        )}

        {/* Bull / Bear */}
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

        {/* Risk assessment + CTA */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          {result.risk_assessment && (
            <div className="flex-1">
              <span className="font-raleway text-xs tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Risk Assessment:{' '}
              </span>
              <p className="font-raleway text-xs mt-1 leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
                {result.risk_assessment.slice(0, 300)}
              </p>
            </div>
          )}

          <div className="flex items-center gap-4 shrink-0">
            <button
              onClick={onExportPDF}
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

// ─── Data Sources Panel ────────────────────────────────────────────────────────

/** Format raw values: large numbers → $1.2B, decimals → %, etc. */
function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'string') return v
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (typeof v === 'number') {
    const abs = Math.abs(v)
    if (abs >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
    if (abs >= 1e9)  return `$${(v / 1e9).toFixed(2)}B`
    if (abs >= 1e6)  return `$${(v / 1e6).toFixed(1)}M`
    if (abs >= 1e3)  return v.toLocaleString()
    // Looks like a ratio / margin (0–1 range)
    if (abs < 10 && abs > 0 && abs !== Math.round(abs)) return `${(v * 100).toFixed(1)}%`
    return v.toFixed(2)
  }
  return String(v)
}

function DataCard({
  title,
  data,
  accent = '#C9A84C',
}: {
  title: string
  data: Record<string, unknown>
  accent?: string
}) {
  const [open, setOpen] = useState(false)
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== '')

  if (entries.length === 0) return null

  return (
    <div style={{ border: '1px solid rgba(255,255,255,0.07)', background: '#0d0d0d' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 transition-colors duration-200 hover:bg-white/[0.02]"
        data-hover
      >
        <span className="font-cinzel text-xs font-semibold tracking-widest uppercase" style={{ color: accent }}>
          {title}
        </span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />
        </motion.div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-1" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              {/* Render "History" / long strings as full-width rows */}
              {entries.map(([k, v]) => {
                const isLong = typeof v === 'string' && v.length > 60
                return isLong ? (
                  <div key={k} className="py-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <p className="font-raleway text-xs mb-1" style={{ color: 'rgba(201,168,76,0.6)' }}>{k}</p>
                    <p className="font-raleway text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)', fontFamily: "'Courier New', monospace" }}>
                      {String(v)}
                    </p>
                  </div>
                ) : (
                  <div key={k} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{k}</span>
                    <span className="font-raleway text-xs font-semibold ml-4 text-right" style={{ color: 'rgba(255,255,255,0.82)' }}>
                      {fmtVal(v)}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function DataSourcesPanel({ snapshot }: { snapshot: DataSnapshot }) {
  const [panelOpen, setPanelOpen] = useState(false)

  const sections: { title: string; key: keyof DataSnapshot; accent?: string }[] = [
    { title: 'Company Overview',         key: 'company',       accent: '#C9A84C' },
    { title: 'Valuation Multiples',      key: 'valuation',     accent: '#FFD700' },
    { title: 'Profitability & Returns',  key: 'profitability', accent: '#C9A84C' },
    { title: 'Income Statement',         key: 'financials',    accent: '#C9A84C' },
    { title: 'Balance Sheet',            key: 'balance_sheet', accent: '#FFD700' },
    { title: 'Cash Flow',                key: 'cash_flow',     accent: '#C9A84C' },
    { title: 'Growth & SEC History',     key: 'growth',        accent: '#22c55e' },
    { title: 'Technical Indicators',     key: 'technical',     accent: '#C9A84C' },
    { title: 'Market & Share Data',      key: 'market',        accent: '#FFD700' },
    { title: 'Macro & Rates (FRED)',     key: 'macro',         accent: '#C0C0C0' },
    { title: 'Analyst Recommendations', key: 'analyst_recs',  accent: '#C9A84C' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mt-8"
    >
      {/* Section toggle header */}
      <button
        onClick={() => setPanelOpen((o) => !o)}
        className="flex items-center justify-between w-full py-4 group"
        data-hover
      >
        <div className="flex items-center gap-3">
          <Database size={16} style={{ color: 'rgba(201,168,76,0.6)' }} />
          <h3 className="font-cinzel font-semibold text-white text-base">Data Sources</h3>
          <span className="font-raleway text-xs px-2 py-0.5" style={{ background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.2)', color: 'rgba(201,168,76,0.7)' }}>
            yfinance · SEC EDGAR · FRED
          </span>
        </div>
        <motion.div animate={{ rotate: panelOpen ? 180 : 0 }} transition={{ duration: 0.25 }}>
          <ChevronDown size={18} style={{ color: 'rgba(201,168,76,0.5)' }} />
        </motion.div>
      </button>

      <div className="h-px mb-4" style={{ background: 'rgba(201,168,76,0.15)' }} />

      <AnimatePresence>
        {panelOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pb-8 items-start">
              {sections.map(({ title, key, accent }) => (
                <DataCard
                  key={key}
                  title={title}
                  data={(snapshot[key] as Record<string, unknown>) || {}}
                  accent={accent}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function LiveAnalysisPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { events, isConnected, isComplete, finalResult, dataSnapshot, error: wsError, stop } = useWebSocket(sessionId || null)

  // ── Read which personas were selected (stored by AnalyserPage) ────────────
  const [selectedPersonaIds] = useState<Set<string>>(() => {
    if (!sessionId) return new Set<string>()
    try {
      const stored = sessionStorage.getItem(`personas_${sessionId}`)
      if (stored) {
        const arr = JSON.parse(stored) as string[]
        if (arr.length > 0) return new Set(arr)
      }
    } catch { /* ignore */ }
    return new Set<string>()  // empty = treat all as selected
  })

  const selectedPersonaCount = selectedPersonaIds.size || PERSONAS.length

  // ── Build agent list — all 15 shown, unselected get a fun "not in action" label
  const [agents, setAgents] = useState<AgentState[]>(() =>
    PERSONAS.map((p, i) => {
      const isSelected = selectedPersonaIds.size === 0 || selectedPersonaIds.has(p.id)
      return {
        id: p.id,
        name: p.name,
        initials: p.initials,
        status: 'pending' as AgentStatus,
        isSelected,
        notSelectedLabel: NOT_SELECTED_LABEL,
      }
    })
  )

  const [thoughtLines, setThoughtLines] = useState<ThoughtLine[]>([])
  const [bullLines, setBullLines] = useState<string[]>([])
  const [bearLines, setBearLines] = useState<string[]>([])
  const timelineBottomRef = useRef<HTMLDivElement>(null)
  const lineCounter = useRef(0)
  // BUG-17 fix: track last-processed event index so batched arrivals aren't dropped
  const lastProcessedIdx = useRef(-1)

  // Pipeline step progress (non-persona agents: data fetchers, debate, PM)
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(() =>
    PIPELINE_STEP_DEFS.map((s) => ({ ...s, status: 'pending' as PipelineStatus }))
  )

  // Read ticker from sessionStorage (stored by AnalyserPage before navigating)
  const [ticker] = useState<string>(() => {
    if (!sessionId) return 'STOCK'
    return (
      sessionStorage.getItem(`ticker_${sessionId}`) ||
      sessionStorage.getItem('last_ticker') ||
      'STOCK'
    )
  })

  // ── Process incoming WebSocket events ────────────────────────────────────────
  // BUG-17 fix: process ALL new events since last run, not just events[last]
  // This prevents batched state updates from silently dropping agent_start signals.
  useEffect(() => {
    const newEvents = events.slice(lastProcessedIdx.current + 1)
    if (newEvents.length === 0) return
    lastProcessedIdx.current = events.length - 1

    for (const ev of newEvents) {
      // Normalise field names — backend uses 'agent'+'message', not 'agent_id'+'content'
      const agentId   = getAgentId(ev)
      const agentText = getEventText(ev)
      const agentName = agentId ? getAgentName(agentId, ev.agent_name) : undefined

      // Add to thought stream (skip empty events like debate_start which have no text)
      if (agentText || ev.type === 'debate_start') {
        const displayText = agentText || (ev.type === 'debate_start' ? '⚔  Bull vs Bear debate begins' : '')
        setThoughtLines((prev) => [
          ...prev.slice(-300),
          { agentName, content: displayText, type: ev.type, id: lineCounter.current++ },
        ])
      }

      switch (ev.type) {
        case 'agent_start':
          if (agentId) {
            if (PIPELINE_AGENT_IDS.has(agentId)) {
              // Pipeline step → update pipeline bar
              setPipelineSteps((prev) =>
                prev.map((s) => s.id === agentId ? { ...s, status: 'running' } : s)
              )
            } else {
              // Persona agent → update timeline
              setAgents((prev) => prev.map((a) => a.id === agentId ? { ...a, status: 'running' } : a))
            }
          }
          break

        case 'agent_progress':
          if (agentId && PIPELINE_AGENT_IDS.has(agentId)) {
            // Keep pipeline step as running (progress event, not complete yet)
          }
          break

        case 'agent_complete':
          if (agentId) {
            if (PIPELINE_AGENT_IDS.has(agentId)) {
              setPipelineSteps((prev) =>
                prev.map((s) => s.id === agentId ? { ...s, status: 'complete' } : s)
              )
            } else {
              setAgents((prev) =>
                prev.map((a) =>
                  a.id === agentId
                    ? {
                        ...a,
                        status: 'complete',
                        signal: normalizeSignal(ev.signal),
                        summary: ev.reasoning || ev.summary || agentText,
                      }
                    : a
                )
              )
              timelineBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
            }
          }
          break

        // Backend sends type="debate_message" + side="bull"|"bear"
        case 'debate_message':
          if (ev.side === 'bull' && agentText) setBullLines((prev) => [...prev, agentText])
          if (ev.side === 'bear' && agentText) setBearLines((prev) => [...prev, agentText])
          break

        // Fallback for legacy event types
        case 'debate_bull':
          if (agentText) setBullLines((prev) => [...prev, agentText])
          break
        case 'debate_bear':
          if (agentText) setBearLines((prev) => [...prev, agentText])
          break
      }
    }
  }, [events.length]) // eslint-disable-line

  const completedCount = agents.filter((a) => a.status === 'complete').length

  // ── Auto-save to localStorage when analysis completes ────────────────────────
  useEffect(() => {
    if (!isComplete || !finalResult || !ticker) return
    try {
      const entry = {
        id: sessionId || String(Date.now()),
        ticker,
        verdict:       finalResult.verdict,
        confidence:    finalResult.confidence,
        target_price:  finalResult.target_price ?? null,
        summary:       finalResult.summary,
        bull_case:     finalResult.bull_case,
        bear_case:     finalResult.bear_case,
        risk_assessment: finalResult.risk_assessment,
        personas:      Array.from(selectedPersonaIds),
        timestamp:     Date.now(),
      }
      const existing = JSON.parse(localStorage.getItem('aurum_history') || '[]') as object[]
      const updated = [entry, ...existing].slice(0, 100)
      localStorage.setItem('aurum_history', JSON.stringify(updated))
    } catch { /* localStorage may be full or disabled */ }
  }, [isComplete]) // eslint-disable-line

  // ── PDF Export ────────────────────────────────────────────────────────────────
  const handleExportPDF = useCallback(() => {
    if (!finalResult || !ticker) return
    const signals = (finalResult.persona_signals || [])
      .map((s) => `<tr><td style="padding:4px 8px;border-bottom:1px solid #222;">${s.agent}</td><td style="padding:4px 8px;border-bottom:1px solid #222;color:${s.signal === 'bullish' ? '#22c55e' : s.signal === 'bearish' ? '#ef4444' : '#aaa'}">${s.signal.toUpperCase()}</td><td style="padding:4px 8px;border-bottom:1px solid #222;">${s.confidence}%</td></tr>`)
      .join('')
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>AURUM AI — ${ticker} Analysis</title>
<style>
  body{font-family:'Georgia',serif;background:#0a0a0a;color:#e5e5e5;margin:0;padding:32px;max-width:900px;margin:0 auto;}
  h1{font-family:'Palatino Linotype',serif;color:#C9A84C;font-size:2.5rem;letter-spacing:.15em;margin-bottom:4px;}
  h2{font-family:'Palatino Linotype',serif;color:#C9A84C;font-size:1.1rem;letter-spacing:.1em;border-bottom:1px solid #333;padding-bottom:8px;margin-top:28px;}
  .meta{color:#888;font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:24px;}
  .verdict{font-size:4rem;font-family:'Palatino Linotype',serif;font-weight:bold;color:${finalResult.verdict.includes('BUY') ? '#C9A84C' : finalResult.verdict.includes('SELL') ? '#ef4444' : '#aaa'};margin:24px 0 8px;}
  .conf{color:#888;font-size:.9rem;}
  .box{background:#111;border:1px solid #222;padding:16px 20px;margin-bottom:16px;}
  table{width:100%;border-collapse:collapse;font-size:.85rem;}
  th{text-align:left;padding:6px 8px;color:#C9A84C;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid #333;}
  .footer{margin-top:48px;padding-top:16px;border-top:1px solid #222;color:#555;font-size:.75rem;}
  @media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
</style></head><body>
<h1>AURUM AI</h1>
<p class="meta">Stock Analysis Report &nbsp;·&nbsp; ${ticker} &nbsp;·&nbsp; ${new Date().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})}</p>
<div class="verdict">${finalResult.verdict}</div>
${finalResult.target_price ? `<p class="conf">Target Price: <strong style="color:#C9A84C">$${finalResult.target_price.toFixed(2)}</strong> &nbsp;·&nbsp; Confidence: ${finalResult.confidence}%</p>` : `<p class="conf">Confidence: ${finalResult.confidence}%</p>`}
<h2>Executive Summary</h2>
<div class="box"><p style="line-height:1.6;margin:0;">${finalResult.summary}</p></div>
<h2>Bull Case</h2>
<div class="box"><p style="line-height:1.6;margin:0;color:#22c55e">${finalResult.bull_case?.replace(/\n/g,'<br>')}</p></div>
<h2>Bear Case</h2>
<div class="box"><p style="line-height:1.6;margin:0;color:#ef4444">${finalResult.bear_case?.replace(/\n/g,'<br>')}</p></div>
<h2>Risk Assessment</h2>
<div class="box"><p style="line-height:1.6;margin:0;">${finalResult.risk_assessment}</p></div>
<h2>Analyst Signals</h2>
<table><thead><tr><th>Analyst</th><th>Signal</th><th>Confidence</th></tr></thead><tbody>${signals}</tbody></table>
<p class="footer">Generated by AURUM AI · Not financial advice · For educational purposes only</p>
</body></html>`

    const win = window.open('', '_blank')
    if (!win) return
    win.document.write(html)
    win.document.close()
    win.focus()
    setTimeout(() => { win.print() }, 400)
  }, [finalResult, ticker])

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

            <div className="flex items-center gap-4">
              {!isComplete && isConnected && (
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
                      {completedCount} / {selectedPersonaCount} analysts complete
                    </p>
                  </div>
                </div>
              )}
              {!isComplete && isConnected && (
                <button
                  onClick={stop}
                  className="flex items-center gap-1.5 font-raleway text-xs tracking-widest uppercase px-4 py-2 transition-all duration-200 hover:bg-red-900/30"
                  style={{ border: '1px solid rgba(239,68,68,0.4)', color: 'rgba(239,68,68,0.8)' }}
                  title="Stop analysis"
                >
                  <Square size={11} />
                  Stop
                </button>
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
              style={{ background: 'linear-gradient(90deg, #C9A84C, #FFD700)', boxShadow: '0 0 8px rgba(201,168,76,0.4)' }}
              animate={{ width: `${(completedCount / selectedPersonaCount) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {wsError && (
          <div
            className="mb-6 px-5 py-4 font-raleway text-sm flex items-center gap-3"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}
          >
            <AlertCircle size={16} />
            {wsError}
            <Link to="/analyser" className="ml-auto underline text-xs">Start new analysis</Link>
          </div>
        )}

        {/* Two-column layout — both columns locked to the same 70 vh height */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start" style={{ height: '70vh' }}>
          {/* Left — Agent Timeline (scrollable) */}
          <div className="lg:col-span-2 overflow-y-auto" style={{ height: '70vh', background: '#0d0d0d', border: '1px solid rgba(201,168,76,0.1)' }}>
            {/* Pipeline step chips — always visible at top */}
            <PipelineStepsBar steps={pipelineSteps} />
            <div className="p-5">
              <p className="font-cinzel text-xs font-semibold tracking-widest uppercase mb-6" style={{ color: 'rgba(201,168,76,0.6)' }}>
                Analyst Progress
              </p>
              {agents.map((agent, i) => (
                <AgentTimelineItem key={agent.id} agent={agent} isLast={i === agents.length - 1} />
              ))}
              <div ref={timelineBottomRef} />
            </div>
          </div>

          {/* Right — Thought Stream (fills same height via h-full inside ThoughtStream) */}
          <div className="lg:col-span-3" style={{ height: '70vh' }}>
            <ThoughtStream lines={thoughtLines} isConnected={isConnected} />
          </div>
        </div>

        {/* Debate */}
        <AnimatePresence>
          {(bullLines.length > 0 || bearLines.length > 0) && (
            <DebateSection bullLines={bullLines} bearLines={bearLines} />
          )}
        </AnimatePresence>

        {/* Final Result */}
        <AnimatePresence>
          {isComplete && finalResult && (
            <FinalResultBanner result={finalResult} ticker={ticker} onExportPDF={handleExportPDF} />
          )}
        </AnimatePresence>

        {/* Data Sources — shown once the snapshot arrives (just before final result) */}
        {dataSnapshot && <DataSourcesPanel snapshot={dataSnapshot} />}

        {/* Waiting state */}
        {thoughtLines.length === 0 && !isConnected && !wsError && (
          <div className="mt-8 text-center py-16">
            <motion.div
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="font-raleway text-sm"
              style={{ color: 'rgba(201,168,76,0.5)' }}
            >
              Connecting to analysis engine...
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}
