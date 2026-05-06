import { useConnectionStore } from '../store/connectionStore'
import { X } from 'lucide-react'

const colors: Record<string, { bg: string; border: string; color: string }> = {
  success: { bg: '#0d2b0d', border: '#2e7d32', color: '#4caf50' },
  error:   { bg: '#2b0d0d', border: '#7d2e2e', color: '#f44336' },
  warning: { bg: '#2b1f0d', border: '#7d5a2e', color: '#ff9800' },
  info:    { bg: '#142218', border: '#2a4a3a', color: '#45c98f' },
}

export function ToastContainer() {
  const { toasts, removeToast } = useConnectionStore()
  return (
    <div style={{ position: 'fixed', bottom: 32, right: 12, zIndex: 999, display: 'flex', flexDirection: 'column', gap: 5 }}>
      {toasts.map(t => {
        const c = colors[t.type]
        return (
          <div key={t.id} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: c.bg, border: `1px solid ${c.border}`,
            padding: '7px 12px', minWidth: 260, maxWidth: 340,
            fontFamily: 'system-ui, sans-serif', fontSize: 12,
          }}>
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: c.color, flexShrink: 0 }} />
            <span style={{ flex: 1, color: '#ccc' }}>{t.message}</span>
            <X size={12} style={{ cursor: 'pointer', color: '#666' }} onClick={() => removeToast(t.id)} />
          </div>
        )
      })}
    </div>
  )
}
