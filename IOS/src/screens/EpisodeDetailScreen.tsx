import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Image,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';
import { mediaAPI } from '../api/media';
import { Episode } from '../types';
import DrawerMenu from '../components/DrawerMenu';

type EpisodeDetailScreenNavigationProp = StackNavigationProp<RootStackParamList, 'EpisodeDetail'>;
type EpisodeDetailScreenRouteProp = RouteProp<RootStackParamList, 'EpisodeDetail'>;

export default function EpisodeDetailScreen() {
  const navigation = useNavigation<EpisodeDetailScreenNavigationProp>();
  const route = useRoute<EpisodeDetailScreenRouteProp>();
  const { episodeId } = route.params;
  const { serverConfig } = useAuthStore();
  
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    loadEpisodeDetail();
  }, [episodeId]);

  const loadEpisodeDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const episodeData = await mediaAPI.getEpisode(episodeId);
      setEpisode(episodeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load episode details');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayPress = () => {
    if (episode && episode.first_file_id) {
      navigation.navigate('Player', {
        itemId: episode.first_file_id,
        title: episode.title || 'Episode',
      });
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading episode details...</Text>
      </View>
    );
  }

  if (error || !episode) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error || 'Episode not found'}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadEpisodeDetail}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const still = episode.still_original || episode.still;
  const overview = episode.overview || '';
  const airDate = episode.air_date;
  const rating = episode.vote_average;
  const episodeNumber = episode.episode;
  const seasonNumber = episode.season;

  return (
    <>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* Hero Section with Still */}
        <View style={[styles.hero, still && { backgroundColor: '#1a1a1a' }]}>
          {still ? (
            <Image source={{ uri: still }} style={styles.still} resizeMode="cover" />
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
            <View style={styles.heroMeta}>
              <Text style={styles.title}>{episode.title}</Text>
              
              <View style={styles.metaRow}>
                {seasonNumber && episodeNumber ? (
                  <>
                    <Text style={styles.metaText}>
                      S{String(seasonNumber).padStart(2, '0')}E{String(episodeNumber).padStart(2, '0')}
                    </Text>
                    {airDate ? <Text style={styles.metaDivider}> · </Text> : null}
                  </>
                ) : null}
                {airDate ? <Text style={styles.metaText}>{airDate}</Text> : null}
              </View>

              {overview ? (
                <Text style={styles.overview} numberOfLines={4}>{overview}</Text>
              ) : null}

              <View style={styles.actions}>
                {episode.first_file_id && (
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
          {rating && rating > 0 && (
            <View style={styles.statsRow}>
              <View style={styles.stat}>
                <Text style={styles.statLabel}>Rating</Text>
                <Text style={styles.statValue}>⭐ {rating.toFixed(1)}</Text>
              </View>
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
    height: 500,
    position: 'relative',
  },
  still: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  heroOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    position: 'relative',
    zIndex: 10,
  },
  menuButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuButtonText: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: 'bold',
  },
  backButtonText: {
    fontSize: 20,
    color: '#ffffff',
    fontWeight: 'bold',
  },
  heroContent: {
    flex: 1,
    justifyContent: 'flex-end',
    paddingBottom: 30,
    paddingHorizontal: 20,
    position: 'relative',
    zIndex: 10,
  },
  heroMeta: {
    maxWidth: '100%',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
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
    fontSize: 15,
    color: '#ffffff',
    lineHeight: 22,
    marginBottom: 20,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  playButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  playButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  details: {
    padding: 20,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 24,
    marginBottom: 24,
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
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
  },
});
