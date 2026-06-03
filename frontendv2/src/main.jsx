import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import './index.css';
import './styles/theme.css';
import './styles/utilities.css';
import './styles/App.css';
import './styles/LoginPage.css';
import './styles/SignupPage.css';
import './styles/ProfilePage.css';
import './styles/DiscoverPage.css';
import './styles/LikesPage.css';
import './styles/MatchesPage.css';
import './styles/ChatListPage.css';
import './styles/ChatPage.css';
import './styles/UserDetailPage.css';
import './styles/NotificationsPage.css';
import './styles/ForgotPasswordPage.css';
import './styles/ResetPasswordPage.css';
import './styles/RestoreAccountPage.css';
import './styles/Modal.css';
import './styles/SliderPicker.css';
import './styles/Toggle.css';
import './styles/NotificationBell.css';
import './styles/Spinner.css';
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
