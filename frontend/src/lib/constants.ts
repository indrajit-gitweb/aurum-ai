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
    id: "simons",
    name: "Jim Simons",
    style: "Quantitative",
    initials: "JS",
    description: "Pure quant — patterns, signals, statistical edges",
    color: "#C9A84C",
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
    id: "marks",
    name: "Howard Marks",
    style: "Risk-First",
    initials: "HM",
    description: "Market cycles, second-level thinking, risk control",
    color: "#C9A84C",
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
    id: "icahn",
    name: "Carl Icahn",
    style: "Corporate Raiders",
    initials: "CI",
    description: "Unlocking value through pressure on management",
    color: "#C0C0C0",
  },
  {
    id: "templeton",
    name: "John Templeton",
    style: "Global Contrarian",
    initials: "JT",
    description: "Maximum pessimism globally — buy at the point of despair",
    color: "#C9A84C",
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
]

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"

export const SIGNAL_COLORS = {
  BULLISH: '#22c55e',
  BEARISH: '#ef4444',
  NEUTRAL: '#C0C0C0',
} as const

export const VERDICT_CONFIG = {
  BUY: {
    color: '#C9A84C',
    glow: 'rgba(201, 168, 76, 0.4)',
    label: 'BUY',
  },
  HOLD: {
    color: '#C0C0C0',
    glow: 'rgba(192, 192, 192, 0.3)',
    label: 'HOLD',
  },
  SELL: {
    color: '#ef4444',
    glow: 'rgba(239, 68, 68, 0.4)',
    label: 'SELL',
  },
} as const
