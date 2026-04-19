interface Props { rcRate: number; superRate: number; expo: number; color?: string; size?: number }

function calc(stick: number, rc: number, sr: number, expo: number): number {
  const s = Math.abs(stick)
  const e = s * (1 - expo) + s * s * s * expo
  const f = 1 / Math.max(0.01, 1 - s * sr)
  return Math.sign(stick) * Math.min(1980, rc * e * f * 200)
}

export function RatesCurve({ rcRate, superRate, expo, color = '#45c98f', size = 180 }: Props) {
  const W = size, H = size, cx = W / 2, cy = H / 2
  const pts = Array.from({ length: 101 }, (_, i) => {
    const s = (i / 100) * 2 - 1
    return { x: cx + s * cx * 0.88, y: cy - calc(s, rcRate, superRate, expo) / 2000 * cy * 0.88 }
  })
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const maxRate = calc(1, rcRate, superRate, expo).toFixed(0)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={size} height={size} style={{ background: '#111', border: '1px solid #222' }}>
      {/* Grid lines */}
      {[-1,-0.5,0,0.5,1].map(t => (
        <line key={`h${t}`} x1={0} y1={cy+t*cy*0.88} x2={W} y2={cy+t*cy*0.88} stroke="#1e1e1e" strokeWidth={1} />
      ))}
      {[-1,-0.5,0,0.5,1].map(t => (
        <line key={`v${t}`} x1={cx+t*cx*0.88} y1={0} x2={cx+t*cx*0.88} y2={H} stroke="#1e1e1e" strokeWidth={1} />
      ))}
      {/* Axes */}
      <line x1={cx} y1={4} x2={cx} y2={H-4} stroke="#2e2e2e" strokeWidth={1} />
      <line x1={4} y1={cy} x2={W-4} y2={cy} stroke="#2e2e2e" strokeWidth={1} />
      {/* Curve */}
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} />
      {/* Max rate label */}
      <text x={cx+3} y={10} fill="#555" fontSize={9} fontFamily="Fira Code">{maxRate}°/s</text>
    </svg>
  )
}
