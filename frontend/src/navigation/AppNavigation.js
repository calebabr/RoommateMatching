import React from 'react';
import { Text, Platform, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Colors } from '../utils/theme';
import { useAuth } from '../context/AuthContext';

// Screens
import LoginScreen from '../screens/LoginScreen';
import SignupScreen from '../screens/SignupScreen';
import DiscoverScreen from '../screens/DiscoverScreen';
import LikesScreen from '../screens/LikesScreen';
import MatchesScreen from '../screens/MatchesScreen';
import ProfileScreen from '../screens/ProfileScreen';
import UserDetailScreen from '../screens/UserDetailScreen';
import ChatScreen from '../screens/ChatScreen';
import NotificationsScreen from '../screens/NotificationsScreen';

const AuthStack = createNativeStackNavigator();
const UnmatchedTab = createBottomTabNavigator();
const MatchedTab = createBottomTabNavigator();
const RootStack = createNativeStackNavigator();

function AuthNavigator() {
  return (
    <AuthStack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.bg },
      }}
    >
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Signup" component={SignupScreen} />
    </AuthStack.Navigator>
  );
}

function TabIcon({ label, focused }) {
  const icons = {
    Discover: '🔍',
    Likes: '💌',
    Matches: '🤝',
    Profile: '👤',
    Chat: '💬',
  };
  return (
    <Text style={{ fontSize: focused ? 24 : 20, opacity: focused ? 1 : 0.5 }}>
      {icons[label] || '●'}
    </Text>
  );
}

const tabScreenOptions = ({ route }) => ({
  tabBarIcon: ({ focused }) => <TabIcon label={route.name} focused={focused} />,
  tabBarActiveTintColor: Colors.accent,
  tabBarInactiveTintColor: Colors.textMuted,
  tabBarStyle: {
    backgroundColor: Colors.bgCard,
    borderTopColor: Colors.border,
    borderTopWidth: 1,
    height: Platform.OS === 'ios' ? 88 : 64,
    paddingBottom: Platform.OS === 'ios' ? 28 : 8,
    paddingTop: 8,
  },
  tabBarLabelStyle: {
    fontSize: 11,
    fontWeight: '600',
  },
  headerStyle: {
    backgroundColor: Colors.bg,
    borderBottomColor: Colors.border,
    borderBottomWidth: 1,
  },
  headerTintColor: Colors.textPrimary,
  headerTitleStyle: { fontWeight: '700' },
});

/**
 * Tabs shown when user is NOT matched:
 * Discover | Likes | Matches | Profile
 */
function UnmatchedTabs() {
  return (
    <UnmatchedTab.Navigator screenOptions={tabScreenOptions}>
      <UnmatchedTab.Screen
        name="Discover"
        component={DiscoverScreen}
        options={{ headerShown: false }}
      />
      <UnmatchedTab.Screen
        name="Likes"
        component={LikesScreen}
        options={{ headerShown: false }}
      />
      <UnmatchedTab.Screen
        name="Matches"
        component={MatchesScreen}
        options={{ headerShown: false }}
      />
      <UnmatchedTab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ headerShown: false }}
      />
    </UnmatchedTab.Navigator>
  );
}

/**
 * Tabs shown when user IS matched:
 * Chat | Profile
 */
function MatchedTabs() {
  return (
    <MatchedTab.Navigator screenOptions={tabScreenOptions}>
      <MatchedTab.Screen
        name="Chat"
        component={ChatScreen}
        options={{ headerShown: false }}
      />
      <MatchedTab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ headerShown: false }}
      />
    </MatchedTab.Navigator>
  );
}

function AppNavigator() {
  const { user } = useAuth();
  const isMatched = user?.matched === true;

  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      <RootStack.Screen
        name="MainTabs"
        component={isMatched ? MatchedTabs : UnmatchedTabs}
      />
      <RootStack.Screen
        name="UserDetail"
        component={UserDetailScreen}
        options={{ presentation: 'modal' }}
      />
      <RootStack.Screen
        name="Notifications"
        component={NotificationsScreen}
        options={{ presentation: 'modal' }}
      />
    </RootStack.Navigator>
  );
}

export default function AppNavigation() {
  const { user, loading } = useAuth();

  if (loading) {
    return null;
  }

  return (
    <NavigationContainer>
      {user ? <AppNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}