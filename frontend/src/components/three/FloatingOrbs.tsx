import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, useMemo } from 'react'
import * as THREE from 'three'

interface OrbProps {
  position: [number, number, number]
  color: string
  scale: number
  speed: number
  phase: number
}

function Orb({ position, color, scale, speed, phase }: OrbProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.getElapsedTime()
    meshRef.current.position.y = position[1] + Math.sin(t * speed + phase) * 0.8
    meshRef.current.position.x = position[0] + Math.cos(t * speed * 0.7 + phase) * 0.5
    meshRef.current.rotation.y = t * 0.2
    meshRef.current.rotation.z = t * 0.1
  })

  return (
    <mesh ref={meshRef} position={position} scale={scale}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.4}
        roughness={0.1}
        metalness={0.9}
        transparent
        opacity={0.15}
      />
    </mesh>
  )
}

const ORB_DATA: OrbProps[] = [
  { position: [-8, 2, -5], color: '#C9A84C', scale: 3.5, speed: 0.3, phase: 0 },
  { position: [9, -3, -8], color: '#FFD700', scale: 2.8, speed: 0.25, phase: 1.2 },
  { position: [3, 5, -6], color: '#C0C0C0', scale: 2.2, speed: 0.4, phase: 2.4 },
  { position: [-5, -4, -4], color: '#C9A84C', scale: 1.8, speed: 0.35, phase: 0.8 },
  { position: [7, 3, -7], color: '#E8C97A', scale: 3.0, speed: 0.2, phase: 3.6 },
  { position: [-10, 0, -9], color: '#C0C0C0', scale: 4.0, speed: 0.15, phase: 1.8 },
  { position: [0, -6, -6], color: '#FFD700', scale: 2.4, speed: 0.45, phase: 4.2 },
]

function OrbField() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[0, 0, 5]} intensity={0.5} color="#C9A84C" />
      {ORB_DATA.map((orb, i) => (
        <Orb key={i} {...orb} />
      ))}
    </>
  )
}

export default function FloatingOrbs({ className = '' }: { className?: string }) {
  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 10], fov: 50 }}
        gl={{ antialias: false, alpha: true }}
        style={{ background: 'transparent' }}
        dpr={Math.min(window.devicePixelRatio, 1.5)}
      >
        <OrbField />
      </Canvas>
    </div>
  )
}
