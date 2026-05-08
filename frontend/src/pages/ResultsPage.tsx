import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus, Download, RefreshCw } from 'lucide-react'
import { PERSONAS } from '@/lib/constants'
import GoldDivider from '@/components/layout/GoldDivider'

// Placeholder result shape for when navigating directly (real data comes from backend)
const DEMO_RESULT = {
  ticker: 'AAPL',
  verdict: 'BUY' as const,
  confidence: 78,
  executive_summary:
    'Apple Inc. demonstrates exceptional capital allocation, dominant ecosystem lock-in, and strong free cash flow generation. While premium valuation warrants caution, the company\'s Services segment trajectory and AI integration pipeline support continued multiple expansion.',
  bull_case:
    'Services segment growing 20%+ annually. $100B+ annual buybacks. Ecosystem lock-in unrivalled. Apple Intelligence as next platform inflection.',
  bear_case:
    'Hardware saturation in key markets. China regulatory and demand risk. Valuation at 28x forward earnings leaves little margin for error.',
  risk_rating: 'MODERATE',
  analyst_signals: PERSONAS.slice(0, 10).map((p, i) => ({
    id: p.id,
    name: p.name,
    initials: p.initials,
    signal: i % 3 === 0 ? 'BEARISH' : i % 5 === 0 ? 'NEUTRAL' : 'BULLISH',
    summary: 'Based on DCF and qualitative analysis, the stock presents a favorable risk/reward profile at current prices.',
    reasoning:
      'Detailed reasoning placeholder. In a live session this would contain the full LLM output with valuation models, qualitative assessment, and risk factors identified by this specific analyst persona.',
  })),
  metrics: [
    { label: 'P/E (TTM)', value: '29.1x' },
    { label: 'Forward P/E', value: '27.8x' },
    { label: 'P/B', value: '43.2x' },
    { label: 'EV/EBITDA', value: '22.4x' },
    { label: 'FCF Yield', value: '3.4%' },
    { label: 'Div. Yield', value: '0.44%' },
    { label: 'Revenue Growth', value: '+6.1%' },
    { label: 'Net Margin', value: '26.4%' },
  ],
}

// ─── Expandable Analyst Card ───────────────────────────────────────────────────
function AnalystResultCard({
  analyst,
  index,
}: {
  analyst: (typeof DEMO_RESULT.analyst_signals)[number]
  index: number
}) {
  const [expanded, setExpanded] = useState(false)
  const sigColor =
    analyst.signal === 'BULLISH' ? '#22c55e' : analyst.signal === 'BEARISH' ? '#ef4444' : '#C0C0C0'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.04 }}
      className="overflow-hidden"
      style={{
        background: '#111111',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <button
        className="w-full flex items-center gap-4 p-5 text-left transition-all duration-200 hover:bg-white/[0.02]"
        onClick={() => setExpanded((e) => !e)}
        data-hover
      >
        <div
          className="w-10 h-10 shrink-0 flex items-center justify-center font-cinzel font-bold text-sm"
          style={{
            background: `${sigColor}15`,
            border: `1px solid ${sigColor}40`,
            color: sigColor,
          }}
        >
          {analyst.initials}
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-cinzel text-sm font-semibold text-white truncate">{analyst.name}</p>
          <p className="font-raleway text-xs truncate mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {analyst.summary}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span
            className="font-raleway text-xs font-semibold px-2.5 py-1 flex items-center gap-1"
            style={{
              color: sigColor,
              background: `${sigColor}15`,
              border: `1px solid ${sigColor}30`,
            }}
          >
            {analyst.signal === 'BULLISH' && <TrendingUp size={10} />}
            {analyst.signal === 'BEARISH' && <TrendingDown size={10} />}
            {analyst.signal === 'NEUTRAL' && <Minus size={10} />}
            {analyst.signal}
          </span>
          {expanded ? (
            <ChevronUp size={16} style={{ color: 'rgba(255,255,255,0.3)' }} />
          ) : (
            <ChevronDown size={16} style={{ color: 'rgba(255,255,255,0.3)' }} />
          )}
        </div>
      </button>

      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="px-5 pb-5"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
        >
          <p
            className="font-raleway text-sm leading-relaxed pt-4"
            style={{ color: 'rgba(255,255,255,0.55)' }}
          >
            {analyst.reasoning}
          </p>
        </motion.div>
      )}
    </motion.div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [debateOpen, setDebateOpen] = useState(false)

  // In a real app, fetch result by sessionId from backend
  const result = DEMO_RESULT

  const verdictConfig = {
    BUY: { color: '#C9A84C', glow: 'rgba(201,168,76,0.25)', label: 'BUY' },
    HOLD: { color: '#C0C0C0', glow: 'rgba(192,192,192,0.15)', label: 'HOLD' },
    SELL: { color: '#ef4444', glow: 'rgba(239,68,68,0.25)', label: 'SELL' },
  }
  const vConfig = verdictConfig[result.verdict]

  return (
    <div className="min-h-screen pt-20 pb-24 px-6" style={{ background: '#0a0a0a' }}>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="pt-10 pb-8 text-center">
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-3" style={{ color: 'rgba(201,168,76,0.6)' }}>
            Analysis Report
          </p>
          <h1 className="font-cinzel font-bold text-white text-4xl mb-1">{result.ticker}</h1>
          {sessionId && (
            <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Session {sessionId}
            </p>
          )}
        </div>

        {/* Executive Summary Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="p-8 mb-6"
          style={{
            background: 'linear-gradient(135deg, rgba(201,168,76,0.06) 0%, rgba(17,17,17,1) 100%)',
            border: `1px solid ${vConfig.color}40`,
            boxShadow: `0 0 40px ${vConfig.glow}`,
          }}
        >
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-6">
            <div>
              <p className="font-raleway text-xs tracking-widest uppercase mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Consensus Verdict
              </p>
              <div className="flex items-baseline gap-4">
                <span
                  className="font-cinzel font-bold"
                  style={{
                    fontSize: '4rem',
                    lineHeight: 1,
                    color: vConfig.color,
                    textShadow: `0 0 30px ${vConfig.glow}`,
                  }}
                >
                  {vConfig.label}
                </span>
                <span
                  className="font-cinzel font-bold text-2xl"
                  style={{ color: 'rgba(201,168,76,0.6)' }}
                >
                  {result.confidence}%
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                className="flex items-center gap-2 font-raleway text-sm tracking-widest uppercase px-5 py-3 transition-all duration-300 hover:bg-gold/10"
                style={{ border: '1px solid rgba(201,168,76,0.3)', color: '#C9A84C' }}
                data-hover
              >
                <Download size={15} />
                Export PDF
              </button>
              <Link
                to="/analyser"
                className="flex items-center gap-2 font-raleway text-sm tracking-widest uppercase px-5 py-3 text-black"
                style={{ background: 'linear-gradient(135deg, #C9A84C, #FFD700)' }}
                data-hover
              >
                <RefreshCw size={15} />
                New
              </Link>
            </div>
          </div>

          <GoldDivider className="mb-5" />

          <p className="font-cormorant text-lg font-light leading-relaxed" style={{ color: 'rgba(255,255,255,0.7)' }}>
            {result.executive_summary}
          </p>
        </motion.div>

        {/* Bull/Bear */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="p-6" style={{ background: 'rgba(34,197,94,0.04)', border: '1px solid rgba(34,197,94,0.2)' }}>
            <p className="font-cinzel text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: '#22c55e' }}>
              <TrendingUp size={14} /> Bull Case
            </p>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {result.bull_case}
            </p>
          </div>
          <div className="p-6" style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <p className="font-cinzel text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: '#ef4444' }}>
              <TrendingDown size={14} /> Bear Case
            </p>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {result.bear_case}
            </p>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="p-6 mb-6" style={{ background: '#111111', border: '1px solid rgba(255,255,255,0.06)' }}>
          <p className="font-cinzel text-sm font-semibold text-white mb-5">Key Metrics</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {result.metrics.map((m) => (
              <div key={m.label} className="text-center">
                <p className="font-cinzel font-bold text-lg mb-1" style={{ color: '#C9A84C' }}>
                  {m.value}
                </p>
                <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  {m.label}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Risk */}
        <div className="p-5 mb-8 flex items-center gap-4" style={{ background: '#111111', border: '1px solid rgba(255,255,255,0.06)' }}>
          <span className="font-raleway text-xs tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Risk Rating:
          </span>
          <span className="font-cinzel font-bold text-base" style={{ color: '#C9A84C' }}>
            {result.risk_rating}
          </span>
        </div>

        <GoldDivider className="mb-8" />

        {/* Analyst Cards */}
        <div className="mb-8">
          <h2 className="font-cinzel font-semibold text-white text-xl mb-6">Analyst Breakdown</h2>
          <div className="space-y-2">
            {result.analyst_signals.map((analyst, i) => (
              <AnalystResultCard key={analyst.id} analyst={analyst} index={i} />
            ))}
          </div>
        </div>

        {/* Debate (collapsible) */}
        <div>
          <button
            className="flex items-center justify-between w-full py-4"
            onClick={() => setDebateOpen((o) => !o)}
            data-hover
          >
            <h2 className="font-cinzel font-semibold text-white text-xl">Bull/Bear Debate Transcript</h2>
            <motion.div animate={{ rotate: debateOpen ? 180 : 0 }}>
              <ChevronDown size={20} style={{ color: 'rgba(201,168,76,0.5)' }} />
            </motion.div>
          </button>

          {debateOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="overflow-hidden"
            >
              <div className="py-4 space-y-3">
                {['The bull thesis rests on Apple\'s unparalleled ecosystem moat and Services momentum.', 'Bears counter with hardware saturation and China overhang.', 'Bull: Services now 20% of revenue and growing at 20%+ — this transforms the valuation framework.', 'Bear: At 29x earnings, any deceleration triggers multiple compression.'].map((line, i) => (
                  <p key={i} className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>
                    {line}
                  </p>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
