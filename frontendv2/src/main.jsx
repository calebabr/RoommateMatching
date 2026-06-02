import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import './index.css';
import App from './App.jsx';

const _sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (_sentryDsn) {
  Sentry.init({
    dsn: _sentryDsn,
    environment: import.meta.env.VITE_ENV || 'development',
    tracesSampleRate: import.meta.env.VITE_ENV === 'production' ? 0.1 : 0.0,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.request?.headers?.Authorization) {
        event.request.headers.Authorization = '[Filtered]';
      }
      return event;
    },
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
