import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useRef, useMemo, useEffect } from 'react'
import * as THREE from 'three'

const vertexShader = `
  uniform float uTime;
  uniform vec2 uMouse;
  attribute float aScale;
  attribute float aPhase;
  attribute float aSpeed;
  varying float vAlpha;
  varying vec3 vColor;
  attribute vec3 aColor;

  void main() {
    vec3 pos = position;

    // Wave motion
    float wave1 = sin(pos.x * 0.5 + uTime * aSpeed + aPhase) * 0.8;
    float wave2 = cos(pos.z * 0.4 + uTime * aSpeed * 0.7 + aPhase * 1.3) * 0.6;
    float wave3 = sin((pos.x + pos.z) * 0.3 + uTime * aSpeed * 0.5) * 0.4;
    pos.y += wave1 + wave2 + wave3;

    // Mouse parallax
    pos.x += uMouse.x * (pos.y * 0.04 + 0.5);
    pos.z += uMouse.y * (pos.y * 0.03 + 0.3);

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = aScale * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;

    // Alpha based on wave height for sparkle
    vAlpha = 0.4 + 0.6 * abs(sin(uTime * aSpeed + aPhase));
    vColor = aColor;
  }
`

const fragmentShader = `
  varying float vAlpha;
  varying vec3 vColor;

  void main() {
    // Circular soft particle
    vec2 uv = gl_PointCoord - vec2(0.5);
    float dist = length(uv);
    if (dist > 0.5) discard;

    float alpha = (1.0 - dist * 2.0) * vAlpha;
    alpha = pow(alpha, 1.5);
    gl_FragColor = vec4(vColor, alpha);
  }
`

const GOLD = new THREE.Color('#C9A84C')
const GOLD_BRIGHT = new THREE.Color('#FFD700')
const SILVER = new THREE.Color('#C0C0C0')
const GOLD_LIGHT = new THREE.Color('#E8C97A')

function GoldParticles() {
  const meshRef = useRef<THREE.Points>(null)
  const mouse = useRef({ x: 0, y: 0 })
  const { size } = useThree()

  const COUNT = 3000

  const { positions, scales, phases, speeds, colors } = useMemo(() => {
    const positions = new Float32Array(COUNT * 3)
    const scales = new Float32Array(COUNT)
    const phases = new Float32Array(COUNT)
    const speeds = new Float32Array(COUNT)
    const colors = new Float32Array(COUNT * 3)

    const palette = [GOLD, GOLD_BRIGHT, SILVER, GOLD_LIGHT]

    for (let i = 0; i < COUNT; i++) {
      // Spread across a wide plane
      positions[i * 3 + 0] = (Math.random() - 0.5) * 40
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10
      positions[i * 3 + 2] = (Math.random() - 0.5) * 20

      scales[i] = Math.random() * 2.5 + 0.5
      phases[i] = Math.random() * Math.PI * 2
      speeds[i] = Math.random() * 0.5 + 0.2

      // Color: mostly gold, some silver
      const colorChoice = Math.random()
      let c: THREE.Color
      if (colorChoice < 0.45) c = GOLD
      else if (colorChoice < 0.7) c = GOLD_BRIGHT
      else if (colorChoice < 0.85) c = GOLD_LIGHT
      else c = palette[Math.floor(Math.random() * palette.length)]

      colors[i * 3 + 0] = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b
    }

    return { positions, scales, phases, speeds, colors }
  }, [])

  const material = useMemo(() => new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
    },
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }), [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouse.current.x = (e.clientX / size.width - 0.5) * 2
      mouse.current.y = -(e.clientY / size.height - 0.5) * 2
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [size])

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.getElapsedTime()
    material.uniforms.uTime.value = t
    // Smoothly lerp mouse
    const current = material.uniforms.uMouse.value as THREE.Vector2
    current.x += (mouse.current.x - current.x) * 0.05
    current.y += (mouse.current.y - current.y) * 0.05
  })

  return (
    <points ref={meshRef} material={material}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-aScale"
          args={[scales, 1]}
        />
        <bufferAttribute
          attach="attributes-aPhase"
          args={[phases, 1]}
        />
        <bufferAttribute
          attach="attributes-aSpeed"
          args={[speeds, 1]}
        />
        <bufferAttribute
          attach="attributes-aColor"
          args={[colors, 3]}
        />
      </bufferGeometry>
    </points>
  )
}

export default function MoltenGoldScene() {
  return (
    <Canvas
      camera={{ position: [0, 2, 12], fov: 60 }}
      style={{ background: '#0a0a0a' }}
      gl={{ antialias: false, alpha: false }}
      dpr={Math.min(window.devicePixelRatio, 1.5)}
    >
      <GoldParticles />
    </Canvas>
  )
}
