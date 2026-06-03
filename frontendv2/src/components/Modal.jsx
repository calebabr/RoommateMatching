import React from 'react';

export default function Modal({ title, message, onClose, onConfirm, confirmText = 'OK', cancelText = 'Cancel', danger = false }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        {title   && <p className="modal-title">{title}</p>}
        {message && <p className="modal-message">{message}</p>}
        <div className="modal-buttons">
          {onConfirm && (
            <button
              className={`modal-btn ${danger ? 'modal-btn-danger' : 'modal-btn-primary'}`}
              onClick={() => { onConfirm(); onClose(); }}
            >
              {confirmText}
            </button>
          )}
          <button className="modal-btn modal-btn-cancel" onClick={onClose}>
            {onConfirm ? cancelText : 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
}
