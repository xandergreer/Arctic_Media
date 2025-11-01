import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'react-native';
import AppNavigator from './src/navigation/AppNavigator';
import { useAuthStore } from './src/store/authStore';
import { usePreferencesStore } from './src/store/preferencesStore';

export default function App() {
  const { checkAuth, isLoading } = useAuthStore();
  const { loadPreferences } = usePreferencesStore();

  useEffect(() => {
    checkAuth();
    loadPreferences();
  }, [checkAuth, loadPreferences]);

  if (isLoading) {
    // You can add a loading screen here
    return null;
  }

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
