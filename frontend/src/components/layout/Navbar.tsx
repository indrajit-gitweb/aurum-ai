import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X } from 'lucide-react'

const NAV_LINKS = [
  { label: 'Home', path: '/' },
  { label: 'Analyser', path: '/analyser' },
  { label: 'History', path: '/history' },
  { label: 'About', path: '#about' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-500"
      style={{
        background: scrolled ? 'rgba(10,10,10,0.85)' : 'transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(201,168,76,0.1)' : 'none',
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="relative group" data-hover>
          <span className="font-cinzel text-xl font-semibold tracking-[0.2em] text-white group-hover:text-gold transition-colors duration-300">
            AURUM
          </span>
          <div
            className="absolute -bottom-1 left-0 h-px bg-gradient-to-r from-gold to-transparent"
            style={{ width: '100%' }}
          />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => {
            const isActive = location.pathname === link.path
            return (
              <Link
                key={link.path}
                to={link.path}
                className="relative font-raleway text-sm font-medium tracking-wider group"
                style={{ color: isActive ? '#C9A84C' : 'rgba(255,255,255,0.7)' }}
                data-hover
              >
                <span className="group-hover:text-white transition-colors duration-200">
                  {link.label}
                </span>
                <span
                  className="absolute -bottom-1 left-0 h-px bg-gold transition-all duration-300"
                  style={{ width: isActive ? '100%' : '0%' }}
                />
                <span
                  className="absolute -bottom-1 left-0 h-px bg-gold transition-all duration-300 group-hover:w-full"
                  style={{ width: isActive ? '100%' : '0%' }}
                />
              </Link>
            )
          })}
          <Link
            to="/history"
            className="font-raleway text-sm font-medium tracking-wider px-5 py-2 border transition-all duration-300 hover:bg-gold hover:text-black"
            style={{
              borderColor: 'rgba(201,168,76,0.5)',
              color: '#C9A84C',
            }}
            data-hover
          >
            History
          </Link>
        </nav>

        {/* Mobile hamburger */}
        <button
          className="md:hidden text-gold p-1"
          onClick={() => setMenuOpen((o) => !o)}
          data-hover
          aria-label="Toggle menu"
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="md:hidden glass-dark border-t border-gold/10"
          >
            <div className="flex flex-col py-4 px-6 gap-4">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className="font-raleway text-sm tracking-wider text-white/70 hover:text-gold transition-colors duration-200 py-2"
                  data-hover
                >
                  {link.label}
                </Link>
              ))}
              <Link
                to="/history"
                className="font-raleway text-sm font-medium tracking-wider px-5 py-3 border border-gold/50 text-gold text-center"
                data-hover
              >
                History
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
