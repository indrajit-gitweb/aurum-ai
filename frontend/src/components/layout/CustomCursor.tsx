import { useEffect, useRef } from 'react'

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const dot = dotRef.current
    const ring = ringRef.current
    if (!dot || !ring) return

    let mouseX = -100
    let mouseY = -100
    let ringX = -100
    let ringY = -100
    let isHovering = false
    let rafId: number

    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
    }

    const onMouseOver = (e: MouseEvent) => {
      const target = e.target as Element
      const interactive = target.closest('a, button, [role="button"], input, textarea, select, label, [data-hover]')
      isHovering = !!interactive
    }

    const animate = () => {
      // Dot follows instantly
      dot.style.transform = `translate(${mouseX - 4}px, ${mouseY - 4}px)`

      // Ring follows with lag
      ringX += (mouseX - ringX) * 0.12
      ringY += (mouseY - ringY) * 0.12
      ring.style.transform = `translate(${ringX - 20}px, ${ringY - 20}px) scale(${isHovering ? 1.6 : 1})`
      ring.style.borderColor = isHovering ? '#C9A84C' : 'rgba(201,168,76,0.5)'

      rafId = requestAnimationFrame(animate)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseover', onMouseOver)
    rafId = requestAnimationFrame(animate)

    // Hide default cursor
    document.documentElement.style.cursor = 'none'

    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseover', onMouseOver)
      cancelAnimationFrame(rafId)
      document.documentElement.style.cursor = ''
    }
  }, [])

  return (
    <>
      {/* Gold dot */}
      <div
        ref={dotRef}
        className="fixed top-0 left-0 w-2 h-2 rounded-full pointer-events-none z-[9999]"
        style={{
          backgroundColor: '#C9A84C',
          boxShadow: '0 0 8px rgba(201,168,76,0.8)',
          willChange: 'transform',
          transition: 'none',
        }}
      />
      {/* Ring */}
      <div
        ref={ringRef}
        className="fixed top-0 left-0 w-10 h-10 rounded-full pointer-events-none z-[9998]"
        style={{
          border: '1px solid rgba(201,168,76,0.5)',
          willChange: 'transform',
          transition: 'border-color 0.2s ease, transform 0.05s ease',
        }}
      />
    </>
  )
}
