import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion, useInView } from 'framer-motion'
import { ChevronDown, Zap, BarChart2, GitMerge, Shield, Layers, FileText } from 'lucide-react'
import MoltenGoldScene from '@/components/three/MoltenGoldScene'
import FloatingOrbs from '@/components/three/FloatingOrbs'
import GoldDivider from '@/components/layout/GoldDivider'
import { PERSONAS } from '@/lib/constants'

// ─── Section 1: Hero ───────────────────────────────────────────────────────────
function HeroSection() {
  return (
    <section className="relative h-screen w-full flex items-center justify-center overflow-hidden">
      {/* Three.js background */}
      <div className="absolute inset-0 z-0">
        <MoltenGoldScene />
      </div>

      {/* Vignette overlay */}
      <div
        className="absolute inset-0 z-10 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 30%, rgba(10,10,10,0.7) 100%)',
        }}
      />

      {/* Content */}
      <div className="relative z-20 text-center px-6 max-w-5xl mx-auto">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="font-cinzel text-xs tracking-[0.4em] uppercase mb-6"
          style={{ color: '#C0C0C0' }}
        >
          Introducing Aurum AI
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.4 }}
          className="font-cinzel font-bold leading-[1.05] mb-6"
          style={{ fontSize: 'clamp(3rem, 8vw, 7rem)' }}
        >
          <span className="text-white block">Your Private</span>
          <span className="text-gold-shimmer block">Hedge Fund.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.65 }}
          className="font-cormorant text-2xl md:text-3xl font-light mb-10"
          style={{ color: '#C0C0C0' }}
        >
          15 AI analysts. Zero cost.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.85 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            to="/analyser"
            className="group relative font-raleway font-semibold text-sm tracking-widest px-8 py-4 text-black transition-all duration-300 overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #C9A84C 0%, #FFD700 50%, #C9A84C 100%)', backgroundSize: '200% auto' }}
            data-hover
          >
            <span className="relative z-10">Analyse a Stock →</span>
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{ background: 'linear-gradient(135deg, #FFD700 0%, #C9A84C 50%, #FFD700 100%)' }}
            />
          </Link>

          <button
            className="font-raleway font-medium text-sm tracking-widest px-8 py-4 transition-all duration-300 hover:bg-gold/10"
            style={{ border: '1px solid rgba(201,168,76,0.5)', color: '#C9A84C' }}
            data-hover
            onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
          >
            See How It Works
          </button>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4, duration: 0.6 }}
      >
        <span className="font-raleway text-xs tracking-[0.3em] uppercase" style={{ color: 'rgba(201,168,76,0.5)' }}>
          Scroll
        </span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <ChevronDown size={18} style={{ color: 'rgba(201,168,76,0.6)' }} />
        </motion.div>
      </motion.div>
    </section>
  )
}

// ─── Section 2: Analysts Grid ──────────────────────────────────────────────────
function AnalystCard({ persona, index }: { persona: typeof PERSONAS[number]; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.07, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="card-gold-border group relative p-5 rounded-sm"
      style={{ background: '#111111' }}
    >
      {/* 3D tilt on hover via CSS */}
      <div className="transition-transform duration-300 group-hover:[transform:perspective(600px)_rotateX(-3deg)_rotateY(3deg)]">
        <div
          className="w-12 h-12 flex items-center justify-center mb-3 font-cinzel font-bold text-lg"
          style={{
            background: 'rgba(201,168,76,0.1)',
            border: '1px solid rgba(201,168,76,0.25)',
            color: persona.color,
          }}
        >
          {persona.initials}
        </div>
        <h3 className="font-cinzel text-sm font-semibold text-white mb-1">{persona.name}</h3>
        <p
          className="font-raleway text-xs tracking-wider mb-2"
          style={{ color: '#C9A84C' }}
        >
          {persona.style}
        </p>
        <p className="font-raleway text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {persona.description}
        </p>
      </div>
    </motion.div>
  )
}

function AnalystsSection() {
  const titleRef = useRef<HTMLDivElement>(null)
  const inView = useInView(titleRef, { once: true })

  return (
    <section className="relative py-32 px-6 overflow-hidden" style={{ background: '#0a0a0a' }}>
      <FloatingOrbs className="opacity-30" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div ref={titleRef} className="text-center mb-16">
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6 }}
            className="font-raleway text-xs tracking-[0.4em] uppercase mb-4"
            style={{ color: '#C9A84C' }}
          >
            Your Advisory Board
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="font-cinzel font-bold text-white"
            style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}
          >
            Meet Your Analysts
          </motion.h2>
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.3 }}
          >
            <GoldDivider className="max-w-xs mx-auto mt-6" delay={0.4} />
          </motion.div>
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
          {PERSONAS.map((persona, i) => (
            <AnalystCard key={persona.id} persona={persona} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Section 3: How It Works ───────────────────────────────────────────────────
const STEPS = [
  { num: '01', title: 'Enter Ticker', desc: 'Type any stock symbol — NYSE, NASDAQ, global markets' },
  { num: '02', title: 'Choose Analysts', desc: 'Select from 15 legendary investor personas' },
  { num: '03', title: 'Watch AI Work', desc: 'Real-time streaming — watch each analyst think live' },
  { num: '04', title: 'Get the Verdict', desc: 'Consensus BUY / HOLD / SELL with full reasoning' },
]

function HowItWorksSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section id="how-it-works" className="relative py-32 px-6" style={{ background: '#0d0d0d' }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20">
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            Simple Process
          </p>
          <h2 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}>
            How It Works
          </h2>
          <GoldDivider className="max-w-xs mx-auto mt-6" delay={0.2} />
        </div>

        <div ref={ref} className="grid grid-cols-1 md:grid-cols-4 gap-0 relative">
          {/* Connector line */}
          <div
            className="hidden md:block absolute top-10 left-[12.5%] right-[12.5%] h-px"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.3), rgba(201,168,76,0.3), transparent)' }}
          />

          {STEPS.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 50 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: i * 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="relative flex flex-col items-center text-center px-6 py-8"
            >
              {/* Gold numbered circle */}
              <div
                className="relative z-10 w-20 h-20 rounded-full flex items-center justify-center mb-6 font-cinzel font-bold text-2xl"
                style={{
                  background: 'linear-gradient(135deg, rgba(201,168,76,0.15) 0%, rgba(255,215,0,0.05) 100%)',
                  border: '1px solid rgba(201,168,76,0.4)',
                  color: '#FFD700',
                  boxShadow: '0 0 30px rgba(201,168,76,0.1)',
                }}
              >
                {step.num}
              </div>
              <h3 className="font-cinzel font-semibold text-white text-lg mb-3">{step.title}</h3>
              <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {step.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Section 4: Features ────────────────────────────────────────────────────────
const FEATURES = [
  { icon: Zap, title: 'Real-time Analysis', desc: 'Watch each AI analyst think through the stock live — no waiting for a final report.' },
  { icon: GitMerge, title: 'Bull/Bear Debate', desc: 'Analysts argue opposing sides. You see the full intellectual tension play out.' },
  { icon: Shield, title: 'Risk Assessment', desc: 'Tail-risk analysis, volatility profile, Nassim Taleb-style fragility checks.' },
  { icon: BarChart2, title: 'Deep Valuation', desc: 'DCF models, P/E compression, PEG ratios — Damodaran-grade number crunching.' },
  { icon: Layers, title: 'Multi-LLM Fallback', desc: 'Groq → Gemini → OpenRouter. If one fails, the next fires. Always running.' },
  { icon: FileText, title: 'PDF Export', desc: 'Export the full analyst report as a beautifully formatted PDF.' },
]

function FeaturesSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section className="relative py-32 px-6" style={{ background: '#0a0a0a' }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20">
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            The Platform
          </p>
          <h2 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}>
            What's Inside AURUM
          </h2>
          <GoldDivider className="max-w-xs mx-auto mt-6" />
        </div>

        <div ref={ref} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: i * 0.1 }}
                className="group relative p-8 overflow-hidden"
                style={{ background: '#111111', border: '1px solid rgba(201,168,76,0.1)' }}
              >
                {/* Animated border trace on hover */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                  style={{
                    background: 'linear-gradient(135deg, rgba(201,168,76,0.05) 0%, transparent 100%)',
                    boxShadow: 'inset 0 0 0 1px rgba(201,168,76,0.4)',
                  }}
                />

                <div
                  className="w-12 h-12 flex items-center justify-center mb-5"
                  style={{
                    background: 'rgba(201,168,76,0.08)',
                    border: '1px solid rgba(201,168,76,0.2)',
                  }}
                >
                  <Icon size={20} style={{ color: '#C9A84C' }} />
                </div>

                <h3 className="font-cinzel font-semibold text-white text-base mb-3">{feature.title}</h3>
                <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>
                  {feature.desc}
                </p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── Section 5: The Free Promise ────────────────────────────────────────────────
function FreePromiseSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section
      className="relative py-32 px-6 overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #0d0d0d 0%, #111111 100%)' }}
    >
      <FloatingOrbs className="opacity-20" />

      <div className="max-w-5xl mx-auto relative z-10" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8 }}
          className="text-center mb-20"
        >
          <p
            className="font-cormorant text-2xl md:text-3xl font-light mb-4"
            style={{ color: 'rgba(255,255,255,0.6)' }}
          >
            Wall Street spent millions building this.
          </p>
          <p
            className="font-cinzel font-bold"
            style={{
              fontSize: 'clamp(2rem, 5vw, 4rem)',
              background: 'linear-gradient(90deg, #C9A84C, #FFD700, #C9A84C)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            We're giving it to you free.
          </p>
        </motion.div>

        <GoldDivider className="mb-16" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              title: 'Your Keys',
              subtitle: 'BYOK Mode',
              desc: 'Add your own Groq, Gemini, OpenRouter, Cerebras, SambaNova, or NVIDIA keys for unlimited, private analysis.',
              note: 'Full control. Zero data retention.',
            },
            {
              title: 'Our Keys',
              subtitle: 'Shared Pool',
              desc: 'Use our shared API pool at no cost. Rate-limited but always available.',
              note: 'No setup required.',
              featured: true,
            },
            {
              title: 'Always Free',
              subtitle: 'Forever',
              desc: 'No subscriptions. No paywalls. No credit card. AURUM is and will remain free.',
              note: 'Open source on GitHub.',
            },
          ].map((col, i) => (
            <motion.div
              key={col.title}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.3 + i * 0.15 }}
              className="relative p-8 text-center"
              style={{
                background: col.featured ? 'rgba(201,168,76,0.06)' : 'rgba(255,255,255,0.02)',
                border: col.featured
                  ? '1px solid rgba(201,168,76,0.4)'
                  : '1px solid rgba(255,255,255,0.07)',
                boxShadow: col.featured ? '0 0 40px rgba(201,168,76,0.08)' : 'none',
              }}
            >
              <p className="font-cinzel font-bold text-xl mb-1" style={{ color: col.featured ? '#FFD700' : '#C9A84C' }}>
                {col.title}
              </p>
              <p className="font-raleway text-xs tracking-widest uppercase mb-5" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {col.subtitle}
              </p>
              <p className="font-raleway text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {col.desc}
              </p>
              <p className="font-raleway text-xs" style={{ color: 'rgba(201,168,76,0.6)' }}>
                {col.note}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Section 6: About ───────────────────────────────────────────────────────────
const PIPELINE_STEPS_ABOUT = [
  { num: '01', title: 'You enter a ticker',  desc: 'Type any stock symbol — US, UK, Indian (.NS / .BO), or any global market supported by Yahoo Finance.' },
  { num: '02', title: 'Data is fetched',     desc: 'Price history, financials, balance sheet, cash flow, SEC filings, macro indicators (FRED), and the latest news headlines are pulled in parallel.' },
  { num: '03', title: '15 AI minds analyse', desc: 'Each persona runs its own specialist LLM call — DCF for Damodaran, scuttlebutt for Fisher, tail-risk for Taleb, macro setup for Druckenmiller, and so on.' },
  { num: '04', title: 'Bull vs Bear debate', desc: 'The bullish and bearish personas argue their cases. A Research Manager reads both sides, scores conviction, and recommends a position size.' },
  { num: '05', title: 'Verdict is issued',   desc: 'A Portfolio Manager agent synthesises the signals into a STRONG BUY / BUY / HOLD / SELL / STRONG SELL verdict with a target price and confidence score.' },
]

const WHY_BUILT = [
  {
    title: 'Retail investors deserve institutional-grade analysis',
    body:  'Hedge funds have floors of analysts running DCF models, reading SEC filings, tracking macro regimes. Retail investors have a Bloomberg terminal they cannot afford. AURUM closes that gap.',
  },
  {
    title: 'One perspective is never enough',
    body:  'A value investor and a momentum trader see the same stock completely differently. AURUM forces every angle — growth, value, macro, tail risk, news sentiment — into the same room so you see the full picture.',
  },
  {
    title: 'AI should debate, not just answer',
    body:  'Most AI tools give you one opinion. AURUM runs a structured debate. You see where analysts disagree, how strong each case is, and what you\'re betting on when you take a position.',
  },
]

function AboutSection() {
  const ref = useRef<HTMLDivElement>(null)
  const pipelineRef = useRef<HTMLDivElement>(null)
  const whyRef = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const pipelineInView = useInView(pipelineRef, { once: true, margin: '-60px' })
  const whyInView = useInView(whyRef, { once: true, margin: '-60px' })

  return (
    <section
      id="about"
      className="relative px-6"
      style={{ background: '#080808', borderTop: '1px solid rgba(201,168,76,0.08)' }}
    >
      {/* ── Part 1: What is AURUM ─────────────────────────────────────────── */}
      <div className="py-28 max-w-7xl mx-auto" ref={ref}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="text-center mb-16"
        >
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            About AURUM AI
          </p>
          <h2 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(2rem, 4vw, 3.5rem)' }}>
            Your Private Hedge Fund. Free.
          </h2>
          <GoldDivider className="max-w-xs mx-auto mt-6" delay={0.2} />
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-14 items-start">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.15 }}
          >
            <p className="font-cormorant text-2xl font-light leading-relaxed mb-7" style={{ color: 'rgba(255,255,255,0.8)' }}>
              AURUM AI gives any investor access to the combined analytical frameworks of the fifteen
              greatest investors in history — simultaneously, in real time, for free.
            </p>
            <p className="font-raleway text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.55)' }}>
              When you type a ticker, fifteen distinct AI minds — each deeply modelled on a different
              investing legend — independently analyse the stock from their own angle. Warren Buffett
              checks the moat. Nassim Taleb stress-tests for black swans. Aswath Damodaran runs a
              full DCF. Rakesh Jhunjhunwala evaluates the emerging-market growth story.
            </p>
            <p className="font-raleway text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Their signals feed into a structured bull-vs-bear debate, overseen by a Research Manager
              who scores conviction and recommends a position size. A Portfolio Manager then issues
              the final verdict: STRONG BUY, BUY, HOLD, SELL, or STRONG SELL.
            </p>
            <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
              The entire pipeline — data fetching, LLM analysis, debate, synthesis — runs in about
              60-120 seconds, streamed live to your screen.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.25 }}
          >
            {[
              { label: 'Analyst personas',  value: '15 legendary investor archetypes' },
              { label: 'Data sources',      value: 'Yahoo Finance · FRED (macro) · SEC EDGAR (filings)' },
              { label: 'LLM engine',        value: 'Groq · Cerebras · SambaNova · Gemini · OpenRouter (auto-fallback)' },
              { label: 'Supported markets', value: 'NYSE · NASDAQ · LSE · NSE/BSE (add .NS / .BO) · Global' },
              { label: 'Stack',             value: 'FastAPI + WebSockets · React 18 · LangGraph-style pipeline' },
              { label: 'Cost',              value: 'Free forever — add your own API key for unlimited runs' },
              { label: 'Open source',       value: 'MIT License · full source on GitHub' },
            ].map((item, i) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 8 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.4, delay: 0.3 + i * 0.07 }}
                className="flex items-start gap-4 py-3"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              >
                <span className="font-raleway text-xs tracking-widest uppercase shrink-0 pt-0.5 w-36" style={{ color: 'rgba(201,168,76,0.65)' }}>
                  {item.label}
                </span>
                <span className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  {item.value}
                </span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>

      <GoldDivider className="max-w-7xl mx-auto" />

      {/* ── Part 2: How It Analyses ───────────────────────────────────────── */}
      <div className="py-28 max-w-7xl mx-auto" ref={pipelineRef}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={pipelineInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            Under the Hood
          </p>
          <h3 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(1.8rem, 3vw, 2.8rem)' }}>
            How an Analysis Runs
          </h3>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-0 relative">
          <div
            className="hidden md:block absolute top-9 left-[10%] right-[10%] h-px"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.25), rgba(201,168,76,0.25), transparent)' }}
          />
          {PIPELINE_STEPS_ABOUT.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 30 }}
              animate={pipelineInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: i * 0.12 }}
              className="relative flex flex-col items-center text-center px-4 py-6"
            >
              <div
                className="relative z-10 w-16 h-16 flex items-center justify-center mb-5 font-cinzel font-bold text-lg"
                style={{
                  background: 'rgba(201,168,76,0.08)',
                  border: '1px solid rgba(201,168,76,0.35)',
                  color: '#FFD700',
                }}
              >
                {step.num}
              </div>
              <h4 className="font-cinzel font-semibold text-white text-sm mb-2">{step.title}</h4>
              <p className="font-raleway text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <GoldDivider className="max-w-7xl mx-auto" />

      {/* ── Part 3: Why It Was Built ──────────────────────────────────────── */}
      <div className="py-28 max-w-7xl mx-auto" ref={whyRef}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={whyInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="font-raleway text-xs tracking-[0.4em] uppercase mb-4" style={{ color: '#C9A84C' }}>
            The Why
          </p>
          <h3 className="font-cinzel font-bold text-white" style={{ fontSize: 'clamp(1.8rem, 3vw, 2.8rem)' }}>
            Why AURUM Was Built
          </h3>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {WHY_BUILT.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 24 }}
              animate={whyInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: i * 0.12 }}
              className="p-8"
              style={{ background: '#111', border: '1px solid rgba(201,168,76,0.1)' }}
            >
              <div className="w-8 h-px mb-6" style={{ background: '#C9A84C' }} />
              <h4 className="font-cinzel font-semibold text-white text-base mb-4">{item.title}</h4>
              <p className="font-raleway text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>{item.body}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={whyInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-12 p-8 text-center"
          style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.15)' }}
        >
          <p className="font-cormorant text-xl font-light mb-2" style={{ color: 'rgba(255,255,255,0.7)' }}>
            "It will not make you a better trader. It will make you a better <em>thinker</em>."
          </p>
          <p className="font-raleway text-xs tracking-widest uppercase" style={{ color: 'rgba(201,168,76,0.5)' }}>
            That is the only promise AURUM makes.
          </p>
        </motion.div>
      </div>
    </section>
  )
}

// ─── Section 7: Footer ──────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer
      className="relative py-16 px-6"
      style={{ background: '#080808', borderTop: '1px solid rgba(201,168,76,0.1)' }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-8">
          <div>
            <p className="font-cinzel text-2xl font-semibold tracking-[0.2em] mb-2" style={{ color: '#C9A84C' }}>
              AURUM AI
            </p>
            <p className="font-raleway text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
              Built with AI. Free forever.
            </p>
          </div>

          <div className="flex items-center gap-8">
            {['Home', 'Analyser', 'GitHub'].map((link) => (
              <a
                key={link}
                href={link === 'GitHub' ? 'https://github.com' : link === 'Home' ? '/' : '/analyser'}
                className="font-raleway text-xs tracking-widest uppercase transition-colors duration-200 hover:text-gold"
                style={{ color: 'rgba(255,255,255,0.4)' }}
                data-hover
              >
                {link}
              </a>
            ))}
          </div>
        </div>

        <GoldDivider className="mt-10 mb-6" />

        <p className="font-raleway text-xs text-center" style={{ color: 'rgba(255,255,255,0.2)' }}>
          © 2025 AURUM AI — Not financial advice. For educational purposes only.
        </p>
      </div>
    </footer>
  )
}

// ─── Main Export ────────────────────────────────────────────────────────────────
export default function HomePage() {
  return (
    <div className="min-h-screen" style={{ background: '#0a0a0a' }}>
      <HeroSection />
      <AnalystsSection />
      <HowItWorksSection />
      <FeaturesSection />
      <FreePromiseSection />
      <AboutSection />
      <Footer />
    </div>
  )
}
