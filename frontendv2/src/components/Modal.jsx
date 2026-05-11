import React from 'react';
import { Colors, Radius } from '../utils/theme';

export default function Modal({ title, message, onClose, onConfirm, confirmText = 'OK', cancelText = 'Cancel', danger = false }) {
  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.box} onClick={e => e.stopPropagation()}>
        {title   && <p style={S.title}>{title}</p>}
        {message && <p style={S.message}>{message}</p>}
        <div style={S.buttons}>
          {onConfirm && (
            <button
              style={{ ...S.btn, ...(danger ? S.btnDanger : S.btnPrimary) }}
              onClick={() => { onConfirm(); onClose(); }}
            >
              {confirmText}
            </button>
          )}
          <button style={{ ...S.btn, ...S.btnCancel }} onClick={onClose}>
            {onConfirm ? cancelText : 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
}

const S = {
  overlay: {
    position: 'fixed', inset: 0, zIndex: 9999,
    backgroundColor: 'rgba(0,0,0,0.7)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 24,
  },
  box: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: 24,
    width: '100%',
    maxWidth: 380,
    border: `1px solid ${Colors.border}`,
    animation: 'fadeIn 0.15s ease',
  },
  title: { fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 8px' },
  message: { fontSize: 14, color: Colors.textSecondary, margin: '0 0 20px', lineHeight: '20px' },
  buttons: { display: 'flex', gap: 10, flexDirection: 'column' },
  btn: {
    borderRadius: Radius.md, paddingTop: 13, paddingBottom: 13,
    fontSize: 15, fontWeight: 600, border: 'none',
    cursor: 'pointer', width: '100%',
  },
  btnPrimary: { backgroundColor: Colors.accent, color: Colors.black },
  btnDanger:  { backgroundColor: Colors.danger,  color: Colors.white },
  btnCancel:  { backgroundColor: 'transparent', color: Colors.textSecondary, border: `1.5px solid ${Colors.border}` },
};
