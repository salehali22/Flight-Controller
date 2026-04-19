import { MIXER_MOTORS } from './ThreeDModel'

interface Props {
  mixerType?: string
  values?: number[]
  size?: number
}

export function MotorDiagram({ mixerType = 'QUADX', values = [], size = 220 }: Props) {
  const motors = MIXER_MOTORS[mixerType] ?? MIXER_MOTORS.QUADX
  const cx = size / 2, cy = size / 2
  const R = size * 0.36 // arm radius in SVG units

  // Convert normalised -1..1 to SVG coords
  // x maps to SVG x, z maps to SVG y (negative because SVG y is down)
  const toSVG = (m: { x: number; z: number }) => ({
    sx: cx + m.x * R,
    sy: cy - m.z * R,  // flip Z so +Z (forward) is up
  })

  const pct = (v: number) => Math.max(0, Math.min(1, (v - 1000) / 1000))

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
      {/* ── Arms ── */}
      {motors.map((m, i) => {
        const { sx, sy } = toSVG(m)
        return <line key={`arm${i}`} x1={cx} y1={cy} x2={sx} y2={sy} stroke="#2a2a2a" strokeWidth={6} strokeLinecap="round" />
      })}

      {/* ── Body ── */}
      {(() => {
        const r = size * 0.1
        const sides = Math.min(8, Math.max(4, motors.length + 2))
        const pts = Array.from({ length: sides }, (_, i) => {
          const a = (i / sides) * Math.PI * 2 - Math.PI / sides
          return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`
        }).join(' ')
        return (
          <>
            <polygon points={pts} fill="#1a1a1a" stroke="#333" strokeWidth="1.5" />
            {/* Forward arrow */}
            <polygon points={`${cx},${cy - r * 1.15} ${cx - 5},${cy - r * 0.75} ${cx + 5},${cy - r * 0.75}`}
              fill="#45c98f" />
          </>
        )
      })()}

      {/* ── Motors ── */}
      {motors.map((m, i) => {
        const { sx, sy } = toSVG(m)
        const p = pct(values[i] ?? 0)
        const hexColor = '#' + m.color.toString(16).padStart(6, '0')
        const circumference = 2 * Math.PI * 16
        const dashLen = p * circumference

        return (
          <g key={`m${i}`}>
            {/* Throttle ring */}
            {p > 0 && (
              <circle
                cx={sx} cy={sy} r={16}
                fill="none" stroke={hexColor} strokeWidth={3}
                strokeDasharray={`${dashLen} ${circumference}`}
                strokeDashoffset={0}
                transform={`rotate(-90 ${sx} ${sy})`}
                opacity={0.8}
              />
            )}
            {/* Outer ring */}
            <circle cx={sx} cy={sy} r={16} fill="#111" stroke="#333" strokeWidth={1.5} />
            {/* Inner fill */}
            <circle cx={sx} cy={sy} r={9} fill={hexColor} opacity={0.9} />
            {/* Spin direction arc */}
            <path
              d={m.cw
                ? `M ${sx} ${sy - 13} A 13 13 0 0 1 ${sx + 13} ${sy}`
                : `M ${sx + 13} ${sy} A 13 13 0 0 1 ${sx} ${sy - 13}`
              }
              fill="none" stroke={hexColor} strokeWidth={1.5} opacity={0.5}
              markerEnd="url(#arr)"
            />

            {/* Label */}
            <text x={sx} y={sy + 28} textAnchor="middle"
              fill={hexColor} fontSize={11} fontFamily="Fira Code, monospace" fontWeight="600">
              M{i + 1}
            </text>

            {/* Value */}
            {(values[i] ?? 0) > 0 && (
              <text x={sx} y={sy + 40} textAnchor="middle"
                fill="#666" fontSize={9} fontFamily="Fira Code, monospace">
                {values[i]}
              </text>
            )}
          </g>
        )
      })}

      {/* ── Arrow marker ── */}
      <defs>
        <marker id="arr" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" markerHeight="4" orient="auto">
          <path d="M0,0 L6,3 L0,6 L2,3 Z" fill="#888" />
        </marker>
      </defs>
    </svg>
  )
}
