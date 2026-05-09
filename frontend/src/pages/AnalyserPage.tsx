import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Eye, EyeOff, AlertTriangle, RotateCcw, Layers } from 'lucide-react'
import { useAnalysis } from '@/hooks/useAnalysis'
import { PERSONAS, PERSONA_CATEGORIES } from '@/lib/constants'
import type { PersonaId } from '@/lib/constants'
import GoldDivider from '@/components/layout/GoldDivider'

// ─── Gold Input ───────────────────────────────────────────────────────────────
function GoldInput({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
}) {
  const [focused, setFocused] = useState(false)
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  const actualType = isPassword ? (show ? 'text' : 'password') : type
  const hasValue = value.length > 0

  return (
    <div className="relative group">
      <label
        className="absolute left-0 transition-all duration-300 pointer-events-none font-raleway"
        style={{
          top: focused || hasValue ? '-20px' : '14px',
          fontSize: focused || hasValue ? '11px' : '14px',
          color: focused ? '#C9A84C' : 'rgba(255,255,255,0.4)',
          letterSpacing: focused || hasValue ? '0.1em' : '0.05em',
        }}
      >
        {label}
      </label>

      <input
        type={actualType}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={focused ? placeholder : ''}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="w-full bg-transparent font-raleway text-white text-base py-3 pr-10 outline-none"
        style={{
          borderBottom: `1px solid ${focused ? '#C9A84C' : 'rgba(255,255,255,0.15)'}`,
          transition: 'border-color 0.3s ease',
        }}
        data-hover
      />

      {isPassword && (
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute right-0 top-3 text-white/40 hover:text-gold transition-colors"
          data-hover
        >
          {show ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      )}

      {/* Animated focus line */}
      <div
        className="absolute bottom-0 left-0 h-px transition-all duration-500"
        style={{
          width: focused ? '100%' : '0%',
          background: 'linear-gradient(90deg, #C9A84C, #FFD700)',
          boxShadow: '0 0 8px rgba(201,168,76,0.4)',
        }}
      />
    </div>
  )
}

// ─── Persona Card (selectable) ─────────────────────────────────────────────────
function SelectablePersonaCard({
  persona,
  selected,
  onToggle,
}: {
  persona: typeof PERSONAS[number]
  selected: boolean
  onToggle: () => void
}) {
  return (
    <motion.button
      onClick={onToggle}
      whileTap={{ scale: 0.97 }}
      className="relative p-4 text-left transition-all duration-300 w-full"
      style={{
        background: selected ? 'rgba(201,168,76,0.08)' : '#111111',
        border: selected ? '1px solid rgba(201,168,76,0.5)' : '1px solid rgba(255,255,255,0.06)',
        boxShadow: selected ? '0 0 20px rgba(201,168,76,0.08)' : 'none',
      }}
      data-hover
    >
      {selected && (
        <div
          className="absolute top-2 right-2 w-4 h-4 rounded-full flex items-center justify-center"
          style={{ background: '#C9A84C' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-black" />
        </div>
      )}

      <div
        className="w-10 h-10 flex items-center justify-center mb-2 font-cinzel font-bold text-sm"
        style={{
          background: selected ? 'rgba(201,168,76,0.2)' : 'rgba(201,168,76,0.05)',
          border: `1px solid ${selected ? 'rgba(201,168,76,0.5)' : 'rgba(201,168,76,0.15)'}`,
          color: selected ? '#FFD700' : '#C9A84C',
        }}
      >
        {persona.initials}
      </div>

      <p className="font-cinzel text-xs font-semibold text-white mb-0.5 truncate">{persona.name}</p>
      <p className="font-raleway text-xs mb-1" style={{ color: 'rgba(201,168,76,0.7)' }}>
        {persona.style}
      </p>
      <p
        className="font-raleway leading-snug"
        style={{
          color: 'rgba(255,255,255,0.28)',
          fontSize: '10px',
          overflow: 'hidden',
          maxHeight: '28px',
        }}
      >
        {persona.description}
      </p>
    </motion.button>
  )
}

// ─── API Key Row ──────────────────────────────────────────────────────────────
function ApiKeyRow({
  provider,
  value,
  onChange,
}: {
  provider: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2 w-32 shrink-0">
        <div
          className="w-2 h-2 rounded-full"
          style={{ background: value ? '#22c55e' : 'rgba(255,255,255,0.15)' }}
        />
        <span className="font-raleway text-xs tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.5)' }}>
          {provider}
        </span>
      </div>
      <div className="flex-1">
        <GoldInput
          label=""
          value={value}
          onChange={onChange}
          type="password"
          placeholder={`${provider} API key`}
        />
      </div>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function AnalyserPage() {
  const navigate = useNavigate()
  const {
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
  } = useAnalysis()

  const [apiKeysOpen, setApiKeysOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string>('value')

  // Compute which personas to show based on active tab
  const activeCategoryData = PERSONA_CATEGORIES.find((c) => c.id === activeCategory)
  const visiblePersonas =
    activeCategory === 'all'
      ? [...PERSONAS]
      : PERSONAS.filter((p) => activeCategoryData?.personas.includes(p.id as PersonaId))

  // Count selected within the currently visible category
  const selectedInView = visiblePersonas.filter((p) =>
    form.selectedPersonas.includes(p.id as PersonaId)
  ).length

  // "Select all in category" handler — additive (preserves cross-category picks)
  const handleSelectCategory = () => {
    if (activeCategory === 'all') {
      selectAll()
    } else if (activeCategoryData) {
      selectCategory(activeCategoryData.personas as PersonaId[])
    }
  }

  const handleStart = async () => {
    const sessionId = await startAnalysis()
    if (sessionId) {
      sessionStorage.setItem(`ticker_${sessionId}`, form.ticker)
      sessionStorage.setItem('last_ticker', form.ticker)
      sessionStorage.setItem(`personas_${sessionId}`, JSON.stringify(form.selectedPersonas))
      navigate(`/analyze/live/${sessionId}`)
    }
  }

  const selectedCount = form.selectedPersonas.length
  const tokenEstimate = selectedCount * 800

  return (
    <div className="min-h-screen pt-20 pb-32 px-6" style={{ background: '#0a0a0a' }}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="text-center mb-16 pt-12"
        >
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            Private Analysis
          </p>
          <h1 className="font-cinzel font-bold text-white mb-4" style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}>
            Analyse a Stock
          </h1>
          <p className="font-cormorant text-xl font-light" style={{ color: 'rgba(255,255,255,0.5)' }}>
            Configure your private advisory session
          </p>
        </motion.div>

        <GoldDivider className="mb-16" />

        {/* Step 1 — Ticker + Dates */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-14"
        >
          <div className="flex items-center gap-3 mb-8">
            <span className="font-cinzel font-bold text-2xl" style={{ color: 'rgba(201,168,76,0.4)' }}>01</span>
            <h2 className="font-cinzel font-semibold text-white text-lg">Target Security</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            <div className="pt-6">
              <GoldInput
                label="Stock Ticker"
                value={form.ticker}
                onChange={setTicker}
                placeholder="AAPL"
              />
              <p className="font-raleway text-xs mt-2" style={{ color: 'rgba(255,255,255,0.3)' }}>
                NYSE · NASDAQ · Global markets
              </p>
              <p className="font-raleway text-xs mt-1" style={{ color: 'rgba(201,168,76,0.45)' }}>
                Indian stocks: add{' '}
                <span style={{ fontFamily: 'monospace', color: 'rgba(201,168,76,0.7)' }}>.NS</span> for NSE
                or{' '}
                <span style={{ fontFamily: 'monospace', color: 'rgba(201,168,76,0.7)' }}>.BO</span> for BSE
                &nbsp;(e.g. <span style={{ fontFamily: 'monospace' }}>RELIANCE.NS</span>)
              </p>
            </div>

            <div className="pt-6">
              <GoldInput
                label="Analysis Start"
                value={form.startDate}
                onChange={setStartDate}
                type="date"
              />
            </div>

            <div className="pt-6">
              <GoldInput
                label="Analysis End"
                value={form.endDate}
                onChange={setEndDate}
                type="date"
              />
            </div>
          </div>
        </motion.div>

        <GoldDivider className="mb-14" />

        {/* Step 2 — Persona Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="mb-14"
        >
          {/* Section header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <span className="font-cinzel font-bold text-2xl" style={{ color: 'rgba(201,168,76,0.4)' }}>02</span>
              <h2 className="font-cinzel font-semibold text-white text-lg">Select Your Analysts</h2>
            </div>
            <button
              onClick={resetToDefault}
              className="flex items-center gap-2 font-raleway text-xs tracking-widest uppercase px-4 py-2 transition-all duration-200 hover:border-gold/50 hover:text-gold"
              style={{ border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)' }}
              data-hover
            >
              <RotateCcw size={13} />
              Default
            </button>
          </div>

          {/* Category tabs */}
          <div className="flex flex-wrap gap-2 mb-5">
            {PERSONA_CATEGORIES.map((cat) => {
              const selectedInCat = cat.personas.filter((id) =>
                form.selectedPersonas.includes(id as PersonaId)
              ).length
              const isActive = activeCategory === cat.id
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className="flex items-center gap-2 font-raleway text-xs tracking-wide px-4 py-2 transition-all duration-200"
                  style={{
                    background: isActive ? 'rgba(201,168,76,0.08)' : 'transparent',
                    border: `1px solid ${isActive ? 'rgba(201,168,76,0.45)' : 'rgba(255,255,255,0.08)'}`,
                    color: isActive ? '#C9A84C' : 'rgba(255,255,255,0.4)',
                  }}
                  data-hover
                >
                  <span>{cat.label}</span>
                  <span
                    className="font-cinzel font-bold px-1.5 py-0.5"
                    style={{
                      fontSize: '10px',
                      background: isActive ? 'rgba(201,168,76,0.15)' : 'rgba(255,255,255,0.05)',
                      color: isActive
                        ? selectedInCat > 0 ? '#FFD700' : 'rgba(201,168,76,0.5)'
                        : 'rgba(255,255,255,0.25)',
                    }}
                  >
                    {selectedInCat}/{cat.personas.length}
                  </span>
                </button>
              )
            })}

            {/* All tab */}
            <button
              onClick={() => setActiveCategory('all')}
              className="flex items-center gap-2 font-raleway text-xs tracking-wide px-4 py-2 transition-all duration-200"
              style={{
                background: activeCategory === 'all' ? 'rgba(201,168,76,0.08)' : 'transparent',
                border: `1px solid ${activeCategory === 'all' ? 'rgba(201,168,76,0.45)' : 'rgba(255,255,255,0.08)'}`,
                color: activeCategory === 'all' ? '#C9A84C' : 'rgba(255,255,255,0.4)',
              }}
              data-hover
            >
              <Layers size={12} />
              <span>All 15</span>
              <span
                className="font-cinzel font-bold px-1.5 py-0.5"
                style={{
                  fontSize: '10px',
                  background: activeCategory === 'all' ? 'rgba(201,168,76,0.15)' : 'rgba(255,255,255,0.05)',
                  color: activeCategory === 'all' ? '#FFD700' : 'rgba(255,255,255,0.25)',
                }}
              >
                {selectedCount}/{PERSONAS.length}
              </span>
            </button>
          </div>

          {/* Category use-case description */}
          <AnimatePresence mode="wait">
            {activeCategory !== 'all' && activeCategoryData && (
              <motion.div
                key={activeCategory}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15 }}
                className="mb-4 px-3 py-2"
                style={{ borderLeft: '2px solid rgba(201,168,76,0.3)' }}
              >
                <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
                  {activeCategoryData.useCase}
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Sub-header: token counter + select-category action */}
          <div className="flex items-center justify-between mb-4">
            <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
              {selectedCount} analyst{selectedCount !== 1 ? 's' : ''} selected ·{' '}
              <span style={{ color: 'rgba(201,168,76,0.7)' }}>~{tokenEstimate.toLocaleString()} tokens</span>
              {activeCategory !== 'all' && (
                <span style={{ color: 'rgba(255,255,255,0.2)' }}>
                  {' '}· {selectedInView} of {visiblePersonas.length} in this category
                </span>
              )}
            </p>
            <button
              onClick={handleSelectCategory}
              className="font-raleway text-xs tracking-wide px-3 py-1.5 transition-all duration-200 hover:border-gold/40"
              style={{
                border: '1px solid rgba(201,168,76,0.2)',
                color: 'rgba(201,168,76,0.65)',
              }}
              data-hover
            >
              {activeCategory === 'all' ? 'Select All 15' : `Select All ${activeCategoryData?.label}`}
            </button>
          </div>

          {/* Warning for >10 */}
          <AnimatePresence>
            {selectedCount > 10 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-3 mb-4 px-4 py-3"
                style={{ background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.2)' }}
              >
                <AlertTriangle size={16} style={{ color: '#eab308' }} />
                <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  <span style={{ color: '#eab308' }}>{selectedCount} analysts selected</span> — this will use
                  more tokens and may be slower on shared rate limits
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Persona cards — animated on tab switch */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeCategory}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2"
            >
              {visiblePersonas.map((persona) => (
                <SelectablePersonaCard
                  key={persona.id}
                  persona={persona}
                  selected={form.selectedPersonas.includes(persona.id as PersonaId)}
                  onToggle={() => togglePersona(persona.id as PersonaId)}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        </motion.div>

        <GoldDivider className="mb-14" />

        {/* Step 3 — API Keys (collapsible) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="mb-14"
        >
          <button
            onClick={() => setApiKeysOpen((o) => !o)}
            className="flex items-center justify-between w-full group"
            data-hover
          >
            <div className="flex items-center gap-3">
              <span className="font-cinzel font-bold text-2xl" style={{ color: 'rgba(201,168,76,0.4)' }}>03</span>
              <h2 className="font-cinzel font-semibold text-white text-lg">
                API Keys{' '}
                <span className="font-raleway text-sm font-normal" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  (optional)
                </span>
              </h2>
            </div>
            <motion.div
              animate={{ rotate: apiKeysOpen ? 180 : 0 }}
              transition={{ duration: 0.3 }}
              style={{ color: 'rgba(201,168,76,0.5)' }}
            >
              <ChevronDown size={20} />
            </motion.div>
          </button>

          <AnimatePresence>
            {apiKeysOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div
                  className="mt-6 p-6 space-y-6"
                  style={{ background: '#111111', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    Add your own keys for unlimited access. Your keys are{' '}
                    <span style={{ color: '#C9A84C' }}>never stored</span> — session only.
                    Leave blank to use our shared pool.
                  </p>

                  <ApiKeyRow
                    provider="Groq"
                    value={form.apiKeys.groq}
                    onChange={(v) => setApiKey('groq', v)}
                  />
                  <ApiKeyRow
                    provider="Gemini"
                    value={form.apiKeys.gemini}
                    onChange={(v) => setApiKey('gemini', v)}
                  />
                  <ApiKeyRow
                    provider="OpenRouter"
                    value={form.apiKeys.openrouter}
                    onChange={(v) => setApiKey('openrouter', v)}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-3 mb-8 px-5 py-4"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}
            >
              <AlertTriangle size={16} style={{ color: '#ef4444' }} />
              <p className="font-raleway text-sm" style={{ color: '#ef4444' }}>{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Step 4 — Run */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="text-center"
        >
          <button
            onClick={handleStart}
            disabled={isLoading}
            className="relative group font-cinzel font-bold tracking-[0.2em] text-lg px-16 py-6 text-black transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
            style={{
              background: isLoading
                ? 'rgba(201,168,76,0.5)'
                : 'linear-gradient(135deg, #C9A84C 0%, #FFD700 50%, #C9A84C 100%)',
              backgroundSize: '200% auto',
              minWidth: '320px',
            }}
            data-hover
          >
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{
                background: 'linear-gradient(135deg, #FFD700 0%, #E8C97A 50%, #FFD700 100%)',
              }}
            />
            <span className="relative z-10 flex items-center justify-center gap-3">
              {isLoading ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-5 h-5 rounded-full border-2 border-black border-t-transparent"
                  />
                  Initialising...
                </>
              ) : (
                'Begin Analysis →'
              )}
            </span>
          </button>

          <p className="font-raleway text-xs mt-4" style={{ color: 'rgba(255,255,255,0.25)' }}>
            Powered by Groq, Gemini & OpenRouter
          </p>
        </motion.div>
      </div>
    </div>
  )
}
