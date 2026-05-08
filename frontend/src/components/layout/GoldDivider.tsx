import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'

interface GoldDividerProps {
  className?: string
  delay?: number
}

export default function GoldDivider({ className = '', delay = 0 }: GoldDividerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-50px' })

  return (
    <div ref={ref} className={`relative h-px w-full overflow-hidden ${className}`}>
      {/* Base line */}
      <div className="absolute inset-0 bg-white/5" />
      {/* Animated gold fill */}
      <motion.div
        className="absolute inset-y-0 left-0 h-full"
        initial={{ width: '0%' }}
        animate={inView ? { width: '100%' } : { width: '0%' }}
        transition={{ duration: 1.2, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
        style={{
          background: 'linear-gradient(90deg, transparent 0%, #C9A84C 20%, #FFD700 50%, #C9A84C 80%, transparent 100%)',
        }}
      />
      {/* Shimmer dot */}
      <motion.div
        className="absolute top-1/2 -translate-y-1/2 w-1 h-1 rounded-full"
        initial={{ left: '0%', opacity: 0 }}
        animate={inView ? { left: '100%', opacity: [0, 1, 0] } : { left: '0%', opacity: 0 }}
        transition={{ duration: 1.2, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
        style={{ backgroundColor: '#FFD700', boxShadow: '0 0 6px #FFD700' }}
      />
    </div>
  )
}
