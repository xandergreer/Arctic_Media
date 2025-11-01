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
import { TVShow, Season } from '../types';
import DrawerMenu from '../components/DrawerMenu';

type ShowDetailScreenNavigationProp = StackNavigationProp<RootStackParamList, 'ShowDetail'>;
type ShowDetailScreenRouteProp = RouteProp<RootStackParamList, 'ShowDetail'>;

const { width } = Dimensions.get('window');

export default function ShowDetailScreen() {
  const navigation = useNavigation<ShowDetailScreenNavigationProp>();
  const route = useRoute<ShowDetailScreenRouteProp>();
  const { showId } = route.params;
  const { serverConfig } = useAuthStore();
  
  const [show, setShow] = useState<TVShow | null>(null);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    loadShowDetail();
  }, [showId]);

  const loadShowDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get show details and seasons
      const [showsData, seasonsData] = await Promise.all([
        mediaAPI.getShows(),
        mediaAPI.getSeasons(showId),
      ]);
      
      const showDetail = showsData.find(s => s.id === showId);
      if (!showDetail) {
        throw new Error('Show not found');
      }
      
      setShow(showDetail);
      setSeasons(seasonsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load show details');
    } finally {
      setLoading(false);
    }
  };

  const handleSeasonPress = (season: Season) => {
    const extraJson = (show as any)?.extra_json || {};
    const showPoster = show?.poster_url || extraJson.poster;
    navigation.navigate('Episodes', {
      showId,
      season: season.season || 1,
      showTitle: show?.title || 'TV Show',
      showPoster: showPoster || undefined,
    });
  };

  const handlePlayPress = () => {
    if (show && seasons.length > 0) {
      const extraJson = (show as any)?.extra_json || {};
      const showPoster = show?.poster_url || extraJson.poster;
      // Navigate to first season's first episode
      navigation.navigate('Episodes', {
        showId,
        season: seasons[0].season || 1,
        showTitle: show.title,
        showPoster: showPoster || undefined,
      });
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading show details...</Text>
      </View>
    );
  }

  if (error || !show) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error || 'Show not found'}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadShowDetail}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const extraJson = (show as any).extra_json || {};
  const backdrop = show.backdrop_url || extraJson.backdrop;
  const poster = show.poster_url || extraJson.poster;
  const overview = extraJson.overview || '';
  const genres = extraJson.genres || [];
  const rating = extraJson.vote_average;
  const runtime = extraJson.runtime;
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
                <Text style={styles.posterPlaceholderText}>📺</Text>
              </View>
            )}
            
            <View style={styles.heroMeta}>
              <Text style={styles.title}>
                {show.title}
                {show.year ? <Text style={styles.year}> ({show.year})</Text> : ''}
              </Text>
              
              <View style={styles.metaRow}>
                <Text style={styles.metaText}>TV Series</Text>
                {show.year ? <Text style={styles.metaDivider}> · </Text> : null}
                {show.year ? <Text style={styles.metaText}>{show.year}</Text> : null}
              </View>

              {overview ? (
                <Text style={styles.overview} numberOfLines={4}>{overview}</Text>
              ) : null}

              <View style={styles.actions}>
                {seasons.length > 0 && (
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

          {/* Seasons Section */}
          {seasons.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Seasons</Text>
              <FlatList
                data={seasons}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.seasonCard}
                    onPress={() => handleSeasonPress(item)}
                  >
                    <Image
                      source={{ uri: poster || '' }}
                      style={styles.seasonPoster}
                      resizeMode="cover"
                    />
                    <View style={styles.seasonInfo}>
                      <Text style={styles.seasonTitle}>{item.title}</Text>
                      <Text style={styles.seasonSubtitle}>Season {item.season}</Text>
                    </View>
                    <Text style={styles.seasonArrow}>›</Text>
                  </TouchableOpacity>
                )}
                keyExtractor={(item) => item.id}
                scrollEnabled={false}
              />
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
  seasonCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
  },
  seasonPoster: {
    width: 60,
    height: 90,
    borderRadius: 6,
  },
  seasonInfo: {
    flex: 1,
    marginLeft: 12,
  },
  seasonTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
  },
  seasonSubtitle: {
    fontSize: 12,
    color: '#999999',
  },
  seasonArrow: {
    fontSize: 24,
    color: '#666666',
    marginRight: 8,
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

