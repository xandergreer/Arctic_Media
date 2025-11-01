import React, { useState, useEffect } from 'react';
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
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { Episode } from '../types';

type EpisodesScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Episodes'>;
type EpisodesScreenRouteProp = RouteProp<RootStackParamList, 'Episodes'>;

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 48) / 2; // 2 columns with padding

export default function EpisodesScreen() {
  const navigation = useNavigation<EpisodesScreenNavigationProp>();
  const route = useRoute<EpisodesScreenRouteProp>();
  const { showId, season, showTitle } = route.params;

  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEpisodes();
  }, [showId, season]);

  const loadEpisodes = async () => {
    try {
      setLoading(true);
      setError(null);
      const episodesData = await mediaAPI.getEpisodes(showId, season);
      setEpisodes(episodesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load episodes');
      Alert.alert('Error', 'Failed to load episodes. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEpisodePress = (episode: Episode) => {
    // Use first_file_id if available, otherwise use episode id
    const itemId = episode.first_file_id || episode.id;
    navigation.navigate('Player', {
      itemId: itemId,
      title: episode.title,
    });
  };

  const renderEpisodeItem = ({ item, index }: { item: Episode; index: number }) => {
    const episodeNum = item.episode || (index + 1);
    const episodeTitle = item.title || `Episode ${episodeNum}`;
    
    // Debug: Log episode still URL
    if (item.still) {
      console.log(`Episode ${episodeNum} still URL:`, item.still);
    }
    
    return (
      <TouchableOpacity
        style={styles.episodeCard}
        onPress={() => handleEpisodePress(item)}
        activeOpacity={0.8}
      >
        <View style={styles.episodeImageContainer}>
          {item.still && item.still.trim() !== '' ? (
            <Image
              source={{ uri: item.still }}
              style={styles.episodeImage}
              resizeMode="cover"
              onError={(e) => {
                console.error('Failed to load episode still:', item.still, e.nativeEvent.error);
              }}
            />
          ) : (
            <View style={styles.episodePlaceholder}>
              <Text style={styles.episodePlaceholderText}>{String(episodeNum).padStart(2, '0')}</Text>
            </View>
          )}
          <View style={styles.playOverlay}>
            <View style={styles.playIcon}>
              <Text style={styles.playIconText}>▶</Text>
            </View>
          </View>
        </View>
        <View style={styles.episodeCardMeta}>
          <Text style={styles.episodeCardTitle} numberOfLines={2}>
            {String(episodeNum).padStart(2, '0')} · {episodeTitle}
          </Text>
          {item.air_date && (
            <Text style={styles.episodeCardSubtitle} numberOfLines={1}>
              {new Date(item.air_date).toLocaleDateString()}
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading episodes...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadEpisodes}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={episodes}
        renderItem={renderEpisodeItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        numColumns={2}
        columnWrapperStyle={styles.row}
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
  },
  episodeCard: {
    width: CARD_WIDTH,
    marginBottom: 16,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333333',
  },
  episodeImageContainer: {
    width: '100%',
    aspectRatio: 16 / 9,
    backgroundColor: '#0a0a0a',
    position: 'relative',
  },
  episodeImage: {
    width: '100%',
    height: '100%',
  },
  episodePlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  episodePlaceholderText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#666666',
  },
  playOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  playIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(0, 122, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playIconText: {
    fontSize: 20,
    color: '#ffffff',
    marginLeft: 3,
  },
  episodeCardMeta: {
    padding: 12,
  },
  episodeCardTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
    lineHeight: 18,
  },
  episodeCardSubtitle: {
    fontSize: 11,
    color: '#999999',
  },
});
