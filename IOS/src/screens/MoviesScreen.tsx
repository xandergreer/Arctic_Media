import React, { useState, useEffect, useLayoutEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Image,
  ActivityIndicator,
  Alert,
  Dimensions,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { MediaItem } from '../types';
import OptionsMenu, { GridDensity } from '../components/OptionsMenu';
import { usePreferencesStore } from '../store/preferencesStore';

type MoviesScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Movies'>;

export default function MoviesScreen() {
  const navigation = useNavigation<MoviesScreenNavigationProp>();
  const { movieDensity, setMovieDensity, loadPreferences } = usePreferencesStore();
  const [movies, setMovies] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowWidth, setWindowWidth] = useState(Dimensions.get('window').width);

  useEffect(() => {
    loadMovies();
    loadPreferences();
  }, []);

  useEffect(() => {
    const subscription = Dimensions.addEventListener('change', ({ window }) => {
      setWindowWidth(window.width);
    });
    return () => subscription?.remove();
  }, []);

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => <OptionsMenu density={movieDensity} onDensityChange={setMovieDensity} />,
    });
  }, [navigation, movieDensity, setMovieDensity]);

  const loadMovies = async () => {
    try {
      setLoading(true);
      setError(null);
      const moviesData = await mediaAPI.getAllMovies();
      setMovies(moviesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load movies');
      Alert.alert('Error', 'Failed to load movies. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleMoviePress = (movie: MediaItem) => {
    navigation.navigate('MovieDetail', {
      movieId: movie.id,
    });
  };

  const renderMovieItem = ({ item }: { item: MediaItem }) => {
    const itemWidth = (windowWidth - 48 - (movieDensity - 1) * 8) / movieDensity;
    
    return (
    <TouchableOpacity
      style={[styles.movieItem, { width: itemWidth }]}
      onPress={() => handleMoviePress(item)}
    >
      <View style={styles.posterContainer}>
        {item.poster_url ? (
          <Image
            source={{ uri: item.poster_url }}
            style={styles.poster}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.placeholderPoster}>
            <Text style={styles.placeholderText}>🎬</Text>
          </View>
        )}
      </View>

      <View style={styles.movieInfo}>
        <Text style={styles.movieTitle} numberOfLines={2}>
          {item.title}
        </Text>
        {item.year && (
          <Text style={styles.movieYear}>{item.year}</Text>
        )}
      </View>
    </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading movies...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadMovies}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        key={`grid-${movieDensity}`}
        data={movies}
        renderItem={renderMovieItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        numColumns={movieDensity}
        columnWrapperStyle={movieDensity > 1 ? styles.row : undefined}
        extraData={movieDensity}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 16,
    marginTop: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
    padding: 20,
  },
  errorText: {
    color: '#FF3B30',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  listContainer: {
    padding: 16,
  },
  row: {
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  movieItem: {
    marginBottom: 24,
  },
  posterContainer: {
    width: '100%',
    aspectRatio: 2 / 3,
    marginBottom: 12,
    borderRadius: 8,
    overflow: 'hidden',
  },
  poster: {
    width: '100%',
    height: '100%',
  },
  placeholderPoster: {
    width: '100%',
    height: '100%',
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333333',
  },
  placeholderText: {
    fontSize: 40,
    color: '#666666',
  },
  movieInfo: {
    paddingHorizontal: 4,
  },
  movieTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
    lineHeight: 20,
  },
  movieYear: {
    fontSize: 14,
    color: '#cccccc',
    marginBottom: 2,
  },
});
