import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'react-native';
import AppNavigator from './src/navigation/AppNavigator';
import { useAuthStore } from './src/store/authStore';

export default function App() {
    const { loadPersistedConfig } = useAuthStore();

    useEffect(() => {
        loadPersistedConfig();
    }, [loadPersistedConfig]);

    return (
        <SafeAreaProvider>
            <StatusBar barStyle="light-content" backgroundColor="#000000" />
            <NavigationContainer>
                <AppNavigator />
            </NavigationContainer>
        </SafeAreaProvider>
    );
}
