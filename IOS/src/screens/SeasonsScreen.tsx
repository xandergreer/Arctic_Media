import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
  Dimensions,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { Season } from '../types';
import { useAuthStore } from '../store/authStore';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 48) / 2; // 2 columns with padding

type SeasonsScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Seasons'>;
type SeasonsScreenRouteProp = RouteProp<RootStackParamList, 'Seasons'>;

export default function SeasonsScreen() {
  const navigation = useNavigation<SeasonsScreenNavigationProp>();
  const route = useRoute<SeasonsScreenRouteProp>();
  const { showId, showTitle, showPoster } = route.params;

  const [seasons, setSeasons] = useState<Season[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { serverConfig } = useAuthStore();

  useEffect(() => {
    loadSeasons();
  }, [showId]);

  const loadSeasons = async () => {
    try {
      setLoading(true);
      setError(null);
      const seasonsData = await mediaAPI.getSeasons(showId);
      setSeasons(seasonsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load seasons');
      Alert.alert('Error', 'Failed to load seasons. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSeasonPress = (season: Season) => {
    navigation.navigate('Episodes', {
      showId,
      season: season.season,
      showTitle,
    });
  };

  const renderSeasonItem = ({ item }: { item: Season }) => {
    // Get poster URL - use season poster, show poster, or placeholder
    const posterUrl = item.poster_url || showPoster || (serverConfig?.url ? `${serverConfig.url}/static/img/placeholder.png` : null);
    
    return (
      <TouchableOpacity
        style={styles.seasonCard}
        onPress={() => handleSeasonPress(item)}
        activeOpacity={0.8}
      >
        <View style={styles.seasonImageContainer}>
          {posterUrl ? (
            <Image
              source={{ uri: posterUrl }}
              style={styles.seasonImage}
              resizeMode="cover"
            />
          ) : (
            <View style={styles.seasonPlaceholder}>
              <Text style={styles.seasonPlaceholderText}>S{item.season}</Text>
            </View>
          )}
        </View>
        <View style={styles.seasonCardMeta}>
          <Text style={styles.seasonCardTitle} numberOfLines={1}>
            {item.title}
          </Text>
          {item.season !== null && item.season !== undefined && (
            <Text style={styles.seasonCardSubtitle}>
              Season {item.season}
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
        <Text style={styles.loadingText}>Loading seasons...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadSeasons}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={seasons}
        renderItem={renderSeasonItem}
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
  seasonCard: {
    width: CARD_WIDTH,
    marginBottom: 16,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333333',
  },
  seasonImageContainer: {
    width: '100%',
    aspectRatio: 2 / 3,
    backgroundColor: '#0a0a0a',
  },
  seasonImage: {
    width: '100%',
    height: '100%',
  },
  seasonPlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  seasonPlaceholderText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#666666',
  },
  seasonCardMeta: {
    padding: 12,
  },
  seasonCardTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
  },
  seasonCardSubtitle: {
    fontSize: 12,
    color: '#999999',
  },
});
