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
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { TVShow } from '../types';

type TVShowsScreenNavigationProp = StackNavigationProp<RootStackParamList, 'TVShows'>;

export default function TVShowsScreen() {
  const navigation = useNavigation<TVShowsScreenNavigationProp>();
  const [shows, setShows] = useState<TVShow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadShows();
  }, []);

  const loadShows = async () => {
    try {
      setLoading(true);
      setError(null);
      const showsData = await mediaAPI.getShows();
      setShows(showsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load TV shows');
      Alert.alert('Error', 'Failed to load TV shows. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleShowPress = (show: TVShow) => {
    navigation.navigate('Seasons', {
      showId: show.id,
      showTitle: show.title,
    });
  };

  const renderShowItem = ({ item }: { item: TVShow }) => (
    <TouchableOpacity
      style={styles.showItem}
      onPress={() => handleShowPress(item)}
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
            <Text style={styles.placeholderText}>📺</Text>
          </View>
        )}
      </View>

      <View style={styles.showInfo}>
        <Text style={styles.showTitle} numberOfLines={2}>
          {item.title}
        </Text>
        {item.year && (
          <Text style={styles.showYear}>{item.year}</Text>
        )}
        {item.seasons && (
          <Text style={styles.showSeasons}>
            {item.seasons} Season{item.seasons > 1 ? 's' : ''}
          </Text>
        )}
        {item.episodes && (
          <Text style={styles.showEpisodes}>
            {item.episodes} Episode{item.episodes > 1 ? 's' : ''}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading TV shows...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadShows}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={shows}
        renderItem={renderShowItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        numColumns={2}
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
  showItem: {
    width: '48%',
    marginBottom: 24,
    marginHorizontal: '1%',
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
  showInfo: {
    paddingHorizontal: 4,
  },
  showTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
    lineHeight: 20,
  },
  showYear: {
    fontSize: 14,
    color: '#cccccc',
    marginBottom: 2,
  },
  showSeasons: {
    fontSize: 12,
    color: '#999999',
    marginBottom: 2,
  },
  showEpisodes: {
    fontSize: 12,
    color: '#999999',
  },
});
