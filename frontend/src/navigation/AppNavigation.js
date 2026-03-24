import React from 'react';
import { Text, Platform } from 'react-native';
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
import ChatListScreen from '../screens/ChatListScreen';
import ChatScreen from '../screens/ChatScreen';
import NotificationsScreen from '../screens/NotificationsScreen';

const MAX_MATCHES = 5;

const AuthStack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
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
    Profile: '👤',
    Discover: '🔍',
    Likes: '💌',
    Matches: '🤝',
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
  headerShown: false,
});

function MainTabs() {
  const { user } = useAuth();
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const isFull = matchCount >= MAX_MATCHES;

  return (
    <Tab.Navigator screenOptions={tabScreenOptions} initialRouteName="Profile">
      <Tab.Screen name="Profile" component={ProfileScreen} />
      {!isFull && <Tab.Screen name="Discover" component={DiscoverScreen} />}
      {!isFull && <Tab.Screen name="Likes" component={LikesScreen} />}
      <Tab.Screen name="Matches" component={MatchesScreen} />
      <Tab.Screen name="Chat" component={ChatListScreen} />
    </Tab.Navigator>
  );
}

function AppNavigator() {
  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      <RootStack.Screen name="MainTabs" component={MainTabs} />
      <RootStack.Screen
        name="ChatRoom"
        component={ChatScreen}
        options={{ animation: 'slide_from_right' }}
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

  if (loading) return null;

  return (
    <NavigationContainer>
      {user ? <AppNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
