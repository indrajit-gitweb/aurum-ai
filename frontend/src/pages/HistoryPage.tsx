import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Clock,
  Trash2,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { VERDICT_CONFIG } from '@/lib/constants'

interface HistoryEntry {
  id: string
  ticker: string
  verdict: string
  confidence: number
  target_price: number | null
  summary: string
  timestamp: number
  bull_case?: string
  bear_case?: string
  risk_assessment?: string
  personas?: string[]
}

type DateFilter = 'today' | 'week' | 'month' | 'all'

const DATE_FILTERS: { label: string; value: DateFilter }[] = [
  { label: 'Today', value: 'today' },
  { label: 'This Week', value: 'week' },
  { label: 'This Month', value: 'month' },
  { label: 'All Time', value: 'all' },
]

function getStartOf(filter: DateFilter): number {
  const now = new Date()
  if (filter === 'today') {
    return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  }
  if (filter === 'week') {
    const day = now.getDay()
    const diff = now.getDate() - day + (day === 0 ? -6 : 1)
    return new Date(now.getFullYear(), now.getMonth(), diff).getTime()
  }
  if (filter === 'month') {
    return new Date(now.getFullYear(), now.getMonth(), 1).getTime()
  }
  return 0
}

function VerdictIcon({ verdict }: { verdict: string }) {
  const v = verdict.toUpperCase()
  if (v === 'STRONG BUY' || v === 'BUY') return <TrendingUp size={14} />
  if (v === 'STRONG SELL' || v === 'SELL') return <TrendingDown size={14} />
  return <Minus size={14} />
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [search, setSearch] = useState('')
  const [dateFilter, setDateFilter] = useState<DateFilter>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('aurum_history')
      if (raw) {
        const parsed = JSON.parse(raw) as HistoryEntry[]
        setEntries(parsed.sort((a, b) => b.timestamp - a.timestamp))
      }
    } catch {
      setEntries([])
    }
  }, [])

  function clearHistory() {
    localStorage.removeItem('aurum_history')
    setEntries([])
    setConfirmClear(false)
    setExpandedId(null)
  }

  const startTs = getStartOf(dateFilter)

  const filtered = entries.filter((e) => {
    const matchSearch = e.ticker.toUpperCase().includes(search.toUpperCase().trim())
    const matchDate = dateFilter === 'all' || e.timestamp >= startTs
    return matchSearch && matchDate
  })

  const verdictCfg = (verdict: string) => {
    const key = verdict.toUpperCase() as keyof typeof VERDICT_CONFIG
    return VERDICT_CONFIG[key] ?? { color: '#C0C0C0', glow: 'rgba(192,192,192,0.2)', label: verdict }
  }

  return (
    <div
      className="min-h-screen pt-20"
      style={{ backgroundColor: '#0a0a0a', color: '#fff' }}
    >
      <div className="max-w-7xl mx-auto px-6 py-12">

        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <Clock size={20} style={{ color: '#C9A84C' }} />
            <h1
              className="font-cinzel text-3xl font-semibold tracking-[0.15em]"
              style={{ color: '#C9A84C' }}
            >
              ANALYSIS HISTORY
            </h1>
          </div>
          <p className="font-raleway text-sm tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Your past stock analyses — stored locally in your browser.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-col md:flex-row gap-4 mb-8 items-start md:items-center justify-between">
          {/* Search */}
          <div className="relative w-full md:w-72">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: 'rgba(201,168,76,0.6)' }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search ticker…"
              className="w-full font-raleway text-sm tracking-wider bg-transparent pl-9 pr-4 py-2 outline-none"
              style={{
                border: '1px solid rgba(201,168,76,0.25)',
                color: '#fff',
              }}
            />
          </div>

          {/* Date filter tabs */}
          <div className="flex gap-0">
            {DATE_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setDateFilter(f.value)}
                className="font-raleway text-xs tracking-wider px-4 py-2 transition-all duration-200"
                style={{
                  border: '1px solid rgba(201,168,76,0.2)',
                  marginLeft: '-1px',
                  backgroundColor: dateFilter === f.value ? 'rgba(201,168,76,0.15)' : 'transparent',
                  color: dateFilter === f.value ? '#C9A84C' : 'rgba(255,255,255,0.45)',
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Clear button */}
          {entries.length > 0 && (
            <div className="flex items-center gap-3">
              {confirmClear ? (
                <>
                  <span className="font-raleway text-xs tracking-wider" style={{ color: '#ef4444' }}>
                    Are you sure?
                  </span>
                  <button
                    onClick={clearHistory}
                    className="font-raleway text-xs tracking-wider px-3 py-1.5 transition-all duration-200"
                    style={{
                      border: '1px solid rgba(239,68,68,0.5)',
                      color: '#ef4444',
                    }}
                  >
                    Yes, clear
                  </button>
                  <button
                    onClick={() => setConfirmClear(false)}
                    className="font-raleway text-xs tracking-wider px-3 py-1.5 transition-all duration-200"
                    style={{
                      border: '1px solid rgba(255,255,255,0.15)',
                      color: 'rgba(255,255,255,0.5)',
                    }}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setConfirmClear(true)}
                  className="flex items-center gap-2 font-raleway text-xs tracking-wider px-3 py-1.5 transition-all duration-200 hover:border-red-500/50 hover:text-red-400"
                  style={{
                    border: '1px solid rgba(255,255,255,0.15)',
                    color: 'rgba(255,255,255,0.4)',
                  }}
                >
                  <Trash2 size={12} />
                  Clear History
                </button>
              )}
            </div>
          )}
        </div>

        {/* Result count */}
        {entries.length > 0 && (
          <p className="font-raleway text-xs tracking-wider mb-6" style={{ color: 'rgba(255,255,255,0.3)' }}>
            {filtered.length} {filtered.length === 1 ? 'result' : 'results'}
            {search && ` for "${search.toUpperCase()}"`}
          </p>
        )}

        {/* Empty state */}
        {entries.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center justify-center py-32 gap-6"
            style={{ border: '1px solid rgba(201,168,76,0.1)' }}
          >
            <Clock size={40} style={{ color: 'rgba(201,168,76,0.25)' }} />
            <div className="text-center">
              <p className="font-cinzel text-lg tracking-[0.15em] mb-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
                NO HISTORY YET
              </p>
              <p className="font-raleway text-sm tracking-wider" style={{ color: 'rgba(255,255,255,0.25)' }}>
                Run your first analysis to see results here.
              </p>
            </div>
            <Link
              to="/analyser"
              className="font-raleway text-sm font-medium tracking-wider px-6 py-2.5 transition-all duration-300 hover:bg-gold hover:text-black"
              style={{
                border: '1px solid rgba(201,168,76,0.5)',
                color: '#C9A84C',
              }}
            >
              Analyse a Stock →
            </Link>
          </motion.div>
        )}

        {/* No results after filter */}
        {entries.length > 0 && filtered.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-24 text-center"
          >
            <p className="font-raleway text-sm tracking-wider" style={{ color: 'rgba(255,255,255,0.3)' }}>
              No analyses match your current filter.
            </p>
          </motion.div>
        )}

        {/* Cards */}
        <div className="flex flex-col gap-4">
          <AnimatePresence initial={false}>
            {filtered.map((entry, i) => {
              const cfg = verdictCfg(entry.verdict)
              const isExpanded = expandedId === entry.id

              return (
                <motion.div
                  key={entry.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25, delay: i * 0.04 }}
                  style={{
                    border: `1px solid rgba(201,168,76,0.15)`,
                    backgroundColor: 'rgba(255,255,255,0.02)',
                  }}
                >
                  {/* Card header row */}
                  <button
                    className="w-full text-left px-6 py-5 flex items-center gap-4 md:gap-6"
                    onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  >
                    {/* Ticker */}
                    <div className="flex-shrink-0 w-20">
                      <span
                        className="font-cinzel text-xl font-semibold tracking-widest"
                        style={{ color: '#C9A84C' }}
                      >
                        {entry.ticker}
                      </span>
                    </div>

                    {/* Verdict badge */}
                    <div
                      className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1"
                      style={{
                        border: `1px solid ${cfg.color}40`,
                        backgroundColor: `${cfg.color}12`,
                        color: cfg.color,
                        boxShadow: `0 0 8px ${cfg.glow}`,
                      }}
                    >
                      <VerdictIcon verdict={entry.verdict} />
                      <span className="font-raleway text-xs font-medium tracking-widest">
                        {cfg.label}
                      </span>
                    </div>

                    {/* Confidence */}
                    <div className="flex-shrink-0 hidden sm:block">
                      <span className="font-raleway text-xs tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        Confidence
                      </span>
                      <p className="font-raleway text-sm font-medium" style={{ color: '#fff' }}>
                        {entry.confidence}%
                      </p>
                    </div>

                    {/* Target price */}
                    {entry.target_price != null && (
                      <div className="flex-shrink-0 hidden sm:block">
                        <span className="font-raleway text-xs tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
                          Target
                        </span>
                        <p className="font-raleway text-sm font-medium" style={{ color: '#fff' }}>
                          ${entry.target_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </div>
                    )}

                    {/* Summary preview */}
                    <p
                      className="flex-1 font-raleway text-sm leading-relaxed line-clamp-1 hidden md:block"
                      style={{ color: 'rgba(255,255,255,0.5)' }}
                    >
                      {entry.summary}
                    </p>

                    {/* Date + expand toggle */}
                    <div className="flex-shrink-0 flex items-center gap-4 ml-auto">
                      <div className="text-right hidden sm:block">
                        <p className="font-raleway text-xs tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
                          {formatDate(entry.timestamp)}
                        </p>
                        <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
                          {formatTime(entry.timestamp)}
                        </p>
                      </div>
                      <span style={{ color: 'rgba(201,168,76,0.6)' }}>
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </span>
                    </div>
                  </button>

                  {/* Expanded panel */}
                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        style={{ overflow: 'hidden', borderTop: '1px solid rgba(201,168,76,0.1)' }}
                      >
                        <div className="px-6 py-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Summary */}
                          <div className="md:col-span-2">
                            <p
                              className="font-raleway text-xs tracking-widest uppercase mb-2"
                              style={{ color: 'rgba(201,168,76,0.6)' }}
                            >
                              Summary
                            </p>
                            <p
                              className="font-raleway text-sm leading-relaxed"
                              style={{ color: 'rgba(255,255,255,0.7)' }}
                            >
                              {entry.summary}
                            </p>
                          </div>

                          {/* Bull case */}
                          {entry.bull_case && (
                            <div>
                              <p
                                className="font-raleway text-xs tracking-widest uppercase mb-2 flex items-center gap-1.5"
                                style={{ color: '#22c55e' }}
                              >
                                <TrendingUp size={12} />
                                Bull Case
                              </p>
                              <p
                                className="font-raleway text-sm leading-relaxed"
                                style={{ color: 'rgba(255,255,255,0.65)' }}
                              >
                                {entry.bull_case}
                              </p>
                            </div>
                          )}

                          {/* Bear case */}
                          {entry.bear_case && (
                            <div>
                              <p
                                className="font-raleway text-xs tracking-widest uppercase mb-2 flex items-center gap-1.5"
                                style={{ color: '#ef4444' }}
                              >
                                <TrendingDown size={12} />
                                Bear Case
                              </p>
                              <p
                                className="font-raleway text-sm leading-relaxed"
                                style={{ color: 'rgba(255,255,255,0.65)' }}
                              >
                                {entry.bear_case}
                              </p>
                            </div>
                          )}

                          {/* Risk assessment */}
                          {entry.risk_assessment && (
                            <div className={entry.bull_case && entry.bear_case ? 'md:col-span-2' : ''}>
                              <p
                                className="font-raleway text-xs tracking-widest uppercase mb-2"
                                style={{ color: 'rgba(201,168,76,0.6)' }}
                              >
                                Risk Assessment
                              </p>
                              <p
                                className="font-raleway text-sm leading-relaxed"
                                style={{ color: 'rgba(255,255,255,0.65)' }}
                              >
                                {entry.risk_assessment}
                              </p>
                            </div>
                          )}

                          {/* Personas */}
                          {entry.personas && entry.personas.length > 0 && (
                            <div className="md:col-span-2">
                              <p
                                className="font-raleway text-xs tracking-widest uppercase mb-2"
                                style={{ color: 'rgba(201,168,76,0.6)' }}
                              >
                                Analysts
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {entry.personas.map((p) => (
                                  <span
                                    key={p}
                                    className="font-raleway text-xs tracking-wider px-2 py-1"
                                    style={{
                                      border: '1px solid rgba(201,168,76,0.2)',
                                      color: 'rgba(255,255,255,0.5)',
                                    }}
                                  >
                                    {p}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Mobile date */}
                          <div className="md:col-span-2 sm:hidden">
                            <p
                              className="font-raleway text-xs tracking-wider"
                              style={{ color: 'rgba(255,255,255,0.3)' }}
                            >
                              {formatDate(entry.timestamp)} at {formatTime(entry.timestamp)}
                            </p>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
