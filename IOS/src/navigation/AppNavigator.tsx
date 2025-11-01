import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { useAuthStore } from '../store/authStore';
import ServerConfigScreen from '../screens/ServerConfigScreen';
import LoginScreen from '../screens/LoginScreen';
import HomeScreen from '../screens/HomeScreen';
import TVShowsScreen from '../screens/TVShowsScreen';
import ShowDetailScreen from '../screens/ShowDetailScreen';
import MovieDetailScreen from '../screens/MovieDetailScreen';
import SeasonsScreen from '../screens/SeasonsScreen';
import EpisodesScreen from '../screens/EpisodesScreen';
import PlayerScreen from '../screens/PlayerScreen';
import SettingsScreen from '../screens/SettingsScreen';

export type RootStackParamList = {
  ServerConfig: undefined;
  Login: undefined;
  Home: undefined;
  TVShows: undefined;
  Movies: undefined;
  ShowDetail: { showId: string };
  MovieDetail: { movieId: string };
  Seasons: { showId: string; showTitle: string; showPoster?: string };
  Episodes: { showId: string; season: number; showTitle: string };
  Player: { itemId: string; title: string };
  Settings: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  const { isAuthenticated, serverConfig } = useAuthStore();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#1a1a1a',
        },
        headerTintColor: '#ffffff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
        cardStyle: { backgroundColor: '#000000' },
      }}
    >
      {!serverConfig ? (
        <Stack.Screen
          name="ServerConfig"
          component={ServerConfigScreen}
          options={{ headerShown: false }}
        />
      ) : !isAuthenticated ? (
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />
      ) : (
        <>
          <Stack.Screen
            name="Home"
            component={HomeScreen}
            options={{ title: 'Arctic Media' }}
          />
          <Stack.Screen
            name="TVShows"
            component={TVShowsScreen}
            options={{ title: 'TV Shows' }}
          />
          <Stack.Screen
            name="ShowDetail"
            component={ShowDetailScreen}
            options={{ title: 'TV Show Details', headerShown: false }}
          />
          <Stack.Screen
            name="MovieDetail"
            component={MovieDetailScreen}
            options={{ title: 'Movie Details', headerShown: false }}
          />
          <Stack.Screen
            name="Seasons"
            component={SeasonsScreen}
            options={({ route }) => ({ title: route.params.showTitle })}
          />
          <Stack.Screen
            name="Episodes"
            component={EpisodesScreen}
            options={({ route }) => ({ title: `Season ${route.params.season}` })}
          />
          <Stack.Screen
            name="Player"
            component={PlayerScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{ title: 'Settings' }}
          />
        </>
      )}
    </Stack.Navigator>
  );
}
