import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
  FlatList,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';
import { mediaAPI } from '../api/media';
import { MediaItem } from '../types';
import DrawerMenu from '../components/DrawerMenu';

type MovieDetailScreenNavigationProp = StackNavigationProp<RootStackParamList, 'MovieDetail'>;
type MovieDetailScreenRouteProp = RouteProp<RootStackParamList, 'MovieDetail'>;

const { width } = Dimensions.get('window');

export default function MovieDetailScreen() {
  const navigation = useNavigation<MovieDetailScreenNavigationProp>();
  const route = useRoute<MovieDetailScreenRouteProp>();
  const { movieId } = route.params;
  const { serverConfig } = useAuthStore();
  
  const [movie, setMovie] = useState<MediaItem | null>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    loadMovieDetail();
  }, [movieId]);

  const loadMovieDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get movies list to find this movie
      const movies = await mediaAPI.getRecentMovies(1000); // Get a large number
      const movieDetail = movies.find(m => m.id === movieId);
      
      if (!movieDetail) {
        throw new Error('Movie not found');
      }
      
      // Get files for this movie  
      try {
        const movieFiles = await mediaAPI.getMediaFiles(movieId);
        setFiles(movieFiles);
      } catch (err) {
        console.error('Failed to load files:', err);
        setFiles([]);
      }
      
      setMovie(movieDetail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load movie details');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayPress = () => {
    if (files.length > 0 && movie) {
      // Use first file ID if available, otherwise use movie ID
      const itemId = files[0]?.id || movie.id;
      navigation.navigate('Player', {
        itemId: itemId,
        title: movie.title,
      });
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading movie details...</Text>
      </View>
    );
  }

  if (error || !movie) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error || 'Movie not found'}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadMovieDetail}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const extraJson = (movie as any).extra_json || {};
  const backdrop = movie.backdrop_url || extraJson.backdrop;
  const poster = movie.poster_url || extraJson.poster;
  const overview = extraJson.overview || '';
  const genres = extraJson.genres || [];
  const rating = extraJson.vote_average;
  const runtime = extraJson.runtime || movie.runtime_ms ? Math.round((movie.runtime_ms || 0) / 60000) : null;
  const tagline = extraJson.tagline;
  const releaseDate = extraJson.release_date || movie.year;
  const cast = extraJson.cast || [];

  return (
    <>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* Hero Section with Backdrop */}
        <View style={[styles.hero, backdrop && { backgroundColor: '#1a1a1a' }]}>
          {backdrop ? (
            <Image source={{ uri: backdrop }} style={styles.backdrop} resizeMode="cover" />
          ) : null}
          <View style={styles.heroOverlay} />
          
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.menuButton}
              onPress={() => navigation.goBack()}
            >
              <Text style={styles.backButtonText}>‹ Back</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.menuButton}
              onPress={() => setDrawerVisible(true)}
            >
              <Text style={styles.menuButtonText}>☰</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.heroContent}>
            {poster ? (
              <Image source={{ uri: poster }} style={styles.poster} resizeMode="cover" />
            ) : (
              <View style={styles.posterPlaceholder}>
                <Text style={styles.posterPlaceholderText}>🎬</Text>
              </View>
            )}
            
            <View style={styles.heroMeta}>
              <Text style={styles.title}>
                {movie.title}
                {movie.year ? <Text style={styles.year}> ({movie.year})</Text> : ''}
              </Text>
              
              {tagline && (
                <Text style={styles.tagline}>{tagline}</Text>
              )}

              <View style={styles.metaRow}>
                <Text style={styles.metaText}>Movie</Text>
                {releaseDate ? <Text style={styles.metaDivider}> · </Text> : null}
                {releaseDate ? <Text style={styles.metaText}>{releaseDate}</Text> : null}
              </View>

              {overview ? (
                <Text style={styles.overview} numberOfLines={4}>{overview}</Text>
              ) : null}

              <View style={styles.actions}>
                {files.length > 0 && (
                  <TouchableOpacity style={styles.playButton} onPress={handlePlayPress}>
                    <Text style={styles.playButtonText}>▶ Play</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </View>
        </View>

        {/* Details Section */}
        <View style={styles.details}>
          {genres.length > 0 && (
            <View style={styles.genresContainer}>
              {genres.map((genre: string, index: number) => (
                <View key={index} style={styles.genreTag}>
                  <Text style={styles.genreText}>{genre}</Text>
                </View>
              ))}
            </View>
          )}

          {(rating || runtime) && (
            <View style={styles.statsRow}>
              {rating && (
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>Rating</Text>
                  <Text style={styles.statValue}>⭐ {rating.toFixed(1)}</Text>
                </View>
              )}
              {runtime && (
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>Runtime</Text>
                  <Text style={styles.statValue}>{runtime} min</Text>
                </View>
              )}
            </View>
          )}

          {/* Cast Section */}
          {cast.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Cast</Text>
              <FlatList
                data={cast.slice(0, 10)}
                horizontal
                showsHorizontalScrollIndicator={false}
                renderItem={({ item }: { item: any }) => (
                  <View style={styles.castCard}>
                    {item.profile ? (
                      <Image source={{ uri: item.profile }} style={styles.castImage} resizeMode="cover" />
                    ) : (
                      <View style={styles.castPlaceholder}>
                        <Text style={styles.castPlaceholderText}>👤</Text>
                      </View>
                    )}
                    <Text style={styles.castName} numberOfLines={2}>{item.name}</Text>
                    {item.character && (
                      <Text style={styles.castCharacter} numberOfLines={1}>{item.character}</Text>
                    )}
                  </View>
                )}
                keyExtractor={(item, index) => `${item.name}-${index}`}
                contentContainerStyle={styles.castContainer}
              />
            </View>
          )}
        </View>
      </ScrollView>
      <DrawerMenu visible={drawerVisible} onClose={() => setDrawerVisible(false)} />
    </>
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
  hero: {
    minHeight: 400,
    position: 'relative',
    paddingTop: 60,
  },
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    opacity: 0.5,
  },
  heroOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    zIndex: 10,
  },
  menuButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  menuButtonText: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  heroContent: {
    flexDirection: 'row',
    padding: 20,
    zIndex: 10,
  },
  poster: {
    width: 140,
    height: 210,
    borderRadius: 8,
  },
  posterPlaceholder: {
    width: 140,
    height: 210,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  posterPlaceholderText: {
    fontSize: 60,
  },
  heroMeta: {
    flex: 1,
    marginLeft: 20,
    justifyContent: 'flex-end',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 8,
  },
  year: {
    fontSize: 24,
    fontWeight: 'normal',
    color: '#cccccc',
  },
  tagline: {
    fontSize: 16,
    fontStyle: 'italic',
    color: '#cccccc',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  metaText: {
    fontSize: 14,
    color: '#cccccc',
  },
  metaDivider: {
    fontSize: 14,
    color: '#666666',
  },
  overview: {
    fontSize: 14,
    color: '#ffffff',
    lineHeight: 20,
    marginBottom: 16,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  playButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  playButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  details: {
    padding: 20,
  },
  genresContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 20,
    gap: 8,
  },
  genreTag: {
    backgroundColor: '#333333',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  genreText: {
    color: '#ffffff',
    fontSize: 12,
  },
  statsRow: {
    flexDirection: 'row',
    marginBottom: 24,
    gap: 24,
  },
  stat: {
    alignItems: 'flex-start',
  },
  statLabel: {
    fontSize: 12,
    color: '#999999',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 16,
  },
  castContainer: {
    paddingRight: 20,
  },
  castCard: {
    width: 100,
    marginRight: 16,
    alignItems: 'center',
  },
  castImage: {
    width: 100,
    height: 150,
    borderRadius: 8,
    marginBottom: 8,
  },
  castPlaceholder: {
    width: 100,
    height: 150,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  castPlaceholderText: {
    fontSize: 40,
  },
  castName: {
    fontSize: 12,
    fontWeight: '600',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 2,
  },
  castCharacter: {
    fontSize: 10,
    color: '#999999',
    textAlign: 'center',
  },
});

