import React from 'react'

interface Props {
  open: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
}

export function AlertModal({ open, title, message, onConfirm, onCancel }: Props) {
  if (!open) return null
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 999,
      }}
    >
      <div
        style={{
          background: '#0d1b2e',
          border: '1px solid #1e3a5f',
          borderRadius: '16px',
          padding: '32px',
          maxWidth: '420px',
          width: '90%',
          boxShadow: '0 25px 60px rgba(0,0,0,0.6)',
        }}
      >
        <div style={{ fontSize: '24px', textAlign: 'center', marginBottom: '8px' }}>⚠️</div>
        <h2
          style={{
            fontSize: '18px',
            fontWeight: 700,
            color: '#f8fafc',
            textAlign: 'center',
            marginBottom: '12px',
          }}
        >
          {title}
        </h2>
        <p
          style={{
            fontSize: '14px',
            color: '#c9daea',
            textAlign: 'center',
            lineHeight: 1.7,
            marginBottom: '28px',
          }}
        >
          {message}
        </p>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#94a3b8',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            Batal
          </button>
          <button
            onClick={onConfirm}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #9f1239, #f43f5e)',
              border: 'none',
              color: '#fff',
              fontWeight: 700,
              cursor: 'pointer',
              fontSize: '13px',
              boxShadow: '0 4px 14px rgba(244,63,94,0.35)',
            }}
          >
            🔴 Ya, Tutup Semua!
          </button>
        </div>
      </div>
    </div>
  )
}
