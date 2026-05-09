// Persona list MUST match backend PERSONA_REGISTRY keys exactly.
// Backend file: backend/agents/__init__.py → PERSONA_REGISTRY
export const PERSONAS = [
  {
    id: "buffett",
    name: "Warren Buffett",
    style: "Value Investing",
    initials: "WB",
    description: "Seeks moats, owner earnings & margin of safety",
    color: "#C9A84C",
  },
  {
    id: "munger",
    name: "Charlie Munger",
    style: "Mental Models",
    initials: "CM",
    description: "Applies multidisciplinary mental models to investing",
    color: "#C0C0C0",
  },
  {
    id: "graham",
    name: "Benjamin Graham",
    style: "Deep Value",
    initials: "BG",
    description: "Father of value investing — net-nets & margin of safety",
    color: "#C9A84C",
  },
  {
    id: "lynch",
    name: "Peter Lynch",
    style: "Growth at Value",
    initials: "PL",
    description: "PEG ratio, tenbaggers, invest in what you know",
    color: "#FFD700",
  },
  {
    id: "burry",
    name: "Michael Burry",
    style: "Contrarian Value",
    initials: "MB",
    description: "Deep contrarian digs, leveraged balance sheet analysis",
    color: "#C0C0C0",
  },
  {
    id: "damodaran",
    name: "Aswath Damodaran",
    style: "Valuation",
    initials: "AD",
    description: "DCF master — every asset has intrinsic value",
    color: "#C9A84C",
  },
  {
    id: "druckenmiller",
    name: "Stanley Druckenmiller",
    style: "Macro Momentum",
    initials: "SD",
    description: "Top-down macro with asymmetric conviction bets",
    color: "#FFD700",
  },
  {
    id: "taleb",
    name: "Nassim Taleb",
    style: "Tail Risk",
    initials: "NT",
    description: "Black swans, antifragility & convexity",
    color: "#C0C0C0",
  },
  {
    id: "cathie_wood",
    name: "Cathie Wood",
    style: "Disruptive Growth",
    initials: "CW",
    description: "Exponential technology, 5-year disruption thesis",
    color: "#FFD700",
  },
  {
    id: "ackman",
    name: "Bill Ackman",
    style: "Activist Value",
    initials: "BA",
    description: "Concentrated activist positions with catalysts",
    color: "#C0C0C0",
  },
  {
    id: "fisher",
    name: "Philip Fisher",
    style: "Qualitative Growth",
    initials: "PF",
    description: "Scuttlebutt method — management quality & R&D moats",
    color: "#FFD700",
  },
  {
    id: "pabrai",
    name: "Mohnish Pabrai",
    style: "Dhandho Value",
    initials: "MP",
    description: "Heads I win, tails I don't lose much — Dhandho framework",
    color: "#C9A84C",
  },
  {
    id: "jhunjhunwala",
    name: "Rakesh Jhunjhunwala",
    style: "Emerging Markets",
    initials: "RJ",
    description: "India's Big Bull — GARP with demographic tailwinds",
    color: "#C9A84C",
  },
  {
    id: "growth_agent",
    name: "Growth Analyst",
    style: "Rule of 40",
    initials: "GA",
    description: "Revenue growth, NRR, gross margin expansion",
    color: "#FFD700",
  },
  {
    id: "news_sentiment",
    name: "News Sentiment",
    style: "Event-Driven",
    initials: "NS",
    description: "Aggregates news flow, insider signals & catalysts",
    color: "#C0C0C0",
  },
] as const

export type PersonaId = typeof PERSONAS[number]['id']

export const DEFAULT_PERSONAS: PersonaId[] = [
  "buffett",
  "burry",
  "lynch",
  "damodaran",
  "druckenmiller",
  "taleb",
  "cathie_wood",
  "graham",
  "news_sentiment",
]

// ─── Persona Categories ───────────────────────────────────────────────────────
export interface PersonaCategory {
  id: string
  label: string
  description: string
  useCase: string
  personas: PersonaId[]
}

export const PERSONA_CATEGORIES: PersonaCategory[] = [
  {
    id: 'value',
    label: 'Value',
    description: 'Cheap, undervalued or hated stocks',
    useCase: 'Best for stocks trading below intrinsic value, out-of-favour sectors, distressed businesses, or deep contrarian setups where the market is clearly wrong',
    personas: ['buffett', 'graham', 'munger', 'pabrai', 'burry'],
  },
  {
    id: 'growth',
    label: 'Growth',
    description: 'High-growth, expanding revenue, tech/consumer',
    useCase: 'Best for high-revenue-growth companies, expanding TAMs, SaaS platforms, disruptive technology, and emerging market compounders',
    personas: ['fisher', 'lynch', 'growth_agent', 'jhunjhunwala', 'cathie_wood'],
  },
  {
    id: 'macro',
    label: 'Macro & Activist',
    description: 'Macro-driven bets, turnarounds, activist angle',
    useCase: 'Best when Fed policy, macro cycle positioning, or an activist catalyst (spin-off, buyback, cost restructure) is central to the thesis',
    personas: ['druckenmiller', 'ackman'],
  },
  {
    id: 'risk',
    label: 'Risk & Quant',
    description: 'Tail-risk check, rigorous DCF, market sentiment',
    useCase: 'Best for stress-testing a thesis against black-swan scenarios, running a rigorous DCF, and reading current news flow and insider signals',
    personas: ['taleb', 'damodaran', 'news_sentiment'],
  },
]

// ─── Analysis Window & Mode ──────────────────────────────────────────────────
export const ANALYSIS_WINDOWS = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', 'custom'] as const
export type AnalysisWindow = typeof ANALYSIS_WINDOWS[number]
export type AnalysisMode = 'current' | 'historical'

/** Number of months each preset window represents (custom has no fixed months) */
export const WINDOW_MONTHS: Record<Exclude<AnalysisWindow, 'custom'>, number> = {
  '3M': 3, '6M': 6, '1Y': 12, '2Y': 24, '3Y': 36, '5Y': 60,
}

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"

export const SIGNAL_COLORS = {
  BULLISH: '#22c55e',
  BEARISH: '#ef4444',
  NEUTRAL: '#C0C0C0',
} as const

export const VERDICT_CONFIG = {
  'STRONG BUY': { color: '#22c55e', glow: 'rgba(34,197,94,0.4)', label: 'STRONG BUY' },
  'BUY':        { color: '#C9A84C', glow: 'rgba(201,168,76,0.3)', label: 'BUY' },
  'HOLD':       { color: '#C0C0C0', glow: 'rgba(192,192,192,0.2)', label: 'HOLD' },
  'SELL':       { color: '#ef4444', glow: 'rgba(239,68,68,0.3)', label: 'SELL' },
  'STRONG SELL':{ color: '#dc2626', glow: 'rgba(220,38,38,0.4)', label: 'STRONG SELL' },
} as const
