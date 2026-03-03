# RoomMatch — React Native Frontend

A mobile app for the RoomMatch roommate matching platform. Built with Expo SDK 52 and React Navigation.

## Features

- **Account Creation** — Register with a username and set preferences for 5 matching categories (sleep schedule weekdays/weekends, cleanliness, noise tolerance, guests), each with a value and deal-breaker toggle.
- **Login** — Sign in with your numeric User ID.
- **Discover** — Browse your top compatible roommates ranked by compatibility score. Send likes to people you'd want to live with.
- **Likes** — See who has liked you. Like them back to create a mutual match.
- **Matches** — View confirmed mutual matches with full profile comparison (side-by-side preference breakdown).
- **Profile** — Edit your preferences, view your status, log out, or delete your account.
- **User Detail** — Tap any user card to see their full profile, compatibility score, and preference comparison.
- **Unmatch** — Unmatch from a current roommate to return to the matching pool.

## Backend API Endpoints Used

| Method | Endpoint | Screen |
|--------|----------|--------|
| POST | `/api/users` | Signup |
| GET | `/api/users/{id}` | Login, Detail |
| PUT | `/api/users/{id}` | Profile Edit |
| DELETE | `/api/users/{id}` | Profile Delete |
| GET | `/api/users/{id}/top-matches` | Discover |
| POST | `/api/users/{id}/like` | Discover, Likes, Detail |
| GET | `/api/users/{id}/likes-received` | Likes |
| GET | `/api/users/{id}/matches` | Matches |
| POST | `/api/users/{id}/unmatch` | Matches |
| POST | `/api/matchScore` | Matches, Detail |

## Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure the backend URL**

   By default the app points to `http://localhost:8000/api`. When running on a physical device via Expo Go, you need to use your computer's local IP address instead.

   You can change this in the Login screen by tapping "Server Settings", or by editing `src/services/api.js`.

3. **Start the app**
   ```bash
   npx expo start
   ```

4. **Scan the QR code** with Expo Go on your iOS device.

## Project Structure

```
frontend/
├── App.js                          # Entry point
├── package.json
├── app.json                        # Expo config
├── src/
│   ├── context/
│   │   └── AuthContext.js          # Auth state management
│   ├── navigation/
│   │   └── AppNavigation.js        # Stack + Tab navigation
│   ├── screens/
│   │   ├── LoginScreen.js          # User ID login
│   │   ├── SignupScreen.js         # Account creation + preferences
│   │   ├── DiscoverScreen.js       # Browse compatible users
│   │   ├── LikesScreen.js          # See who liked you
│   │   ├── MatchesScreen.js        # Confirmed matches
│   │   ├── ProfileScreen.js        # View/edit profile
│   │   └── UserDetailScreen.js     # Full user profile view
│   ├── components/
│   │   └── SliderPicker.js         # Custom slider for preferences
│   ├── services/
│   │   └── api.js                  # All backend API calls
│   └── utils/
│       ├── theme.js                # Colors, fonts, radii
│       └── categories.js           # Preference category config
```

## Notes

- The backend doesn't have a traditional auth system (no passwords). The app uses User ID as the login credential and stores the session locally via AsyncStorage.
- Sleep schedule values are in 24-hour format (0–24), representing bedtime hour.
- Deal-breakers cause the compatibility algorithm to reject matches where the difference exceeds a threshold.
- Compatible versions match the user's existing Expo Go setup (SDK 52, React 18.3.1, RN 0.76.5).
