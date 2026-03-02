# RoomMatch — React Native Frontend (Expo)

## Quick Start

```bash
cd frontend
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your phone.

## Connecting to Your Backend

Edit `src/services/api.js` line 13:

```js
// iOS Simulator / Android Emulator (with adb reverse):
const API_BASE = 'http://localhost:8000/api';

// Physical device on Wi-Fi — use your computer's LAN IP:
// const API_BASE = 'http://192.168.1.XX:8000/api';
```

For Android Emulator, also run:
```bash
adb reverse tcp:8000 tcp:8000
```

## Structure

```
frontend/
├── App.js                        ← Entry point
├── app.json                      ← Expo config
├── package.json                  ← Dependencies
├── babel.config.js
├── assets/                       ← App icons (add your own)
└── src/
    ├── components/               ← Reusable UI
    │   ├── Avatar.js
    │   ├── Button.js
    │   ├── CompatBadge.js
    │   ├── PrefTag.js
    │   ├── PreferenceSlider.js
    │   └── Slider.js
    ├── constants/theme.js        ← Colors, spacing, pref config
    ├── hooks/useAuth.js          ← Auth context
    ├── navigation/AppNavigator.js← Stack + tab nav
    ├── screens/
    │   ├── WelcomeScreen.js
    │   ├── LoginScreen.js
    │   ├── RegisterScreen.js     ← 4-step onboarding
    │   ├── DiscoverScreen.js     ← Swipe recommendations
    │   ├── LikesScreen.js        ← Incoming likes
    │   ├── MatchesScreen.js      ← Confirmed matches
    │   └── ProfileScreen.js      ← View/edit/delete
    └── services/api.js           ← All backend API calls
```

## Backend Endpoints Used

| Method | Endpoint                        | Screen         |
|--------|---------------------------------|----------------|
| POST   | /api/users                      | Register       |
| GET    | /api/users/{id}                 | Profile        |
| PUT    | /api/users/{id}                 | Profile edit   |
| DELETE | /api/users/{id}                 | Profile        |
| GET    | /api/users/all                  | Login          |
| GET    | /api/users/{id}/top-matches     | Discover       |
| POST   | /api/users/{id}/like            | Discover/Likes |
| GET    | /api/users/{id}/likes-received  | Likes          |
| GET    | /api/users/{id}/matches         | Matches        |
| POST   | /api/users/{id}/unmatch         | Matches        |
| POST   | /api/matchScore                 | (available)    |
