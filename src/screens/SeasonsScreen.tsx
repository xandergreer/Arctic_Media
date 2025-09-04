import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { Season } from '../types';

type SeasonsScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Seasons'>;
type SeasonsScreenRouteProp = RouteProp<RootStackParamList, 'Seasons'>;

export default function SeasonsScreen() {
  const navigation = useNavigation<SeasonsScreenNavigationProp>();
  const route = useRoute<SeasonsScreenRouteProp>();
  const { showId, showTitle } = route.params;

  const [seasons, setSeasons] = useState<Season[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const renderSeasonItem = ({ item }: { item: Season }) => (
    <TouchableOpacity
      style={styles.seasonItem}
      onPress={() => handleSeasonPress(item)}
    >
      <View style={styles.seasonNumber}>
        <Text style={styles.seasonNumberText}>{item.season}</Text>
      </View>

      <View style={styles.seasonInfo}>
        <Text style={styles.seasonTitle}>{item.title}</Text>
        <Text style={styles.seasonSubtitle}>Tap to view episodes</Text>
      </View>

      <View style={styles.arrowContainer}>
        <Text style={styles.arrowText}>›</Text>
      </View>
    </TouchableOpacity>
  );

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
  seasonItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333333',
  },
  seasonNumber: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  seasonNumberText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  seasonInfo: {
    flex: 1,
  },
  seasonTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  seasonSubtitle: {
    fontSize: 14,
    color: '#cccccc',
  },
  arrowContainer: {
    marginLeft: 16,
  },
  arrowText: {
    fontSize: 24,
    color: '#666666',
    fontWeight: 'bold',
  },
});
