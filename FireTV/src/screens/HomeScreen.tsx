import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Image,
  FlatList,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { useAuthStore } from '../store/authStore';
import { mediaAPI } from '../api/media';
import { TVShow, MediaItem } from '../types';
import DrawerMenu from '../components/DrawerMenu';

type HomeScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Home'>;

const { width } = Dimensions.get('window');
const POSTER_WIDTH = width * 0.35; // Poster cards are about 35% of screen width

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { user, logout, serverConfig } = useAuthStore();
  
  const [recentMovies, setRecentMovies] = useState<MediaItem[]>([]);
  const [recentTVShows, setRecentTVShows] = useState<TVShow[]>([]);
  const [loadingMovies, setLoadingMovies] = useState(true);
  const [loadingTVShows, setLoadingTVShows] = useState(true);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    loadRecentContent();
  }, []);

  const loadRecentContent = async () => {
    try {
      setLoadingMovies(true);
      setLoadingTVShows(true);
      
      const [movies, shows] = await Promise.all([
        mediaAPI.getRecentMovies(20),
        mediaAPI.getRecentTVShows(20),
      ]);
      
      setRecentMovies(movies);
      setRecentTVShows(shows);
    } catch (error) {
      console.error('Failed to load recent content:', error);
    } finally {
      setLoadingMovies(false);
      setLoadingTVShows(false);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const handleMoviePress = (movie: MediaItem) => {
    navigation.navigate('MovieDetail', {
      movieId: movie.id,
    });
  };

  const handleTVShowPress = (show: TVShow) => {
    navigation.navigate('ShowDetail', {
      showId: show.id,
    });
  };

  const navigateToMovies = () => {
    navigation.navigate('Movies');
  };

  const navigateToTVShows = () => {
    navigation.navigate('TVShows');
  };

  const renderMovieCard = ({ item }: { item: MediaItem }) => (
    <TouchableOpacity
      style={styles.posterCard}
      onPress={() => handleMoviePress(item)}
      activeOpacity={0.8}
    >
      <View style={styles.posterContainer}>
        {item.poster_url ? (
          <Image
            source={{ uri: item.poster_url }}
            style={styles.poster}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.posterPlaceholder}>
            <Text style={styles.posterPlaceholderText}>🎬</Text>
          </View>
        )}
      </View>
      <View style={styles.posterMeta}>
        <Text style={styles.posterTitle} numberOfLines={2}>
          {item.title}
        </Text>
        {item.year && (
          <Text style={styles.posterYear}>{item.year}</Text>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderTVShowCard = ({ item }: { item: TVShow }) => (
    <TouchableOpacity
      style={styles.posterCard}
      onPress={() => handleTVShowPress(item)}
      activeOpacity={0.8}
    >
      <View style={styles.posterContainer}>
        {item.poster_url ? (
          <Image
            source={{ uri: item.poster_url }}
            style={styles.poster}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.posterPlaceholder}>
            <Text style={styles.posterPlaceholderText}>📺</Text>
          </View>
        )}
      </View>
      <View style={styles.posterMeta}>
        <Text style={styles.posterTitle} numberOfLines={2}>
          {item.title}
        </Text>
        {item.year && (
          <Text style={styles.posterYear}>{item.year}</Text>
        )}
      </View>
    </TouchableOpacity>
  );

  return (
    <>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.menuButton}
            onPress={() => setDrawerVisible(true)}
          >
            <Text style={styles.menuButtonText}>☰</Text>
          </TouchableOpacity>
          <View style={styles.headerContent}>
            <Text style={styles.welcomeText}>
              Welcome back{user?.username ? `, ${user.username}` : ''}!
            </Text>
            <Text style={styles.serverText} numberOfLines={1}>
              {serverConfig?.url}
            </Text>
          </View>
        </View>

      {/* Recently Added in Movies */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recently Added in Movies</Text>
          <TouchableOpacity onPress={navigateToMovies}>
            <Text style={styles.seeAllText}>See all</Text>
          </TouchableOpacity>
        </View>
        {loadingMovies ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#007AFF" />
          </View>
        ) : recentMovies.length > 0 ? (
          <FlatList
            data={recentMovies}
            renderItem={renderMovieCard}
            keyExtractor={(item) => item.id}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.rowContent}
            ItemSeparatorComponent={() => <View style={{ width: 12 }} />}
          />
        ) : (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No recent movies</Text>
          </View>
        )}
      </View>

      {/* Recently Added in TV */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recently Added in TV</Text>
          <TouchableOpacity onPress={navigateToTVShows}>
            <Text style={styles.seeAllText}>See all</Text>
          </TouchableOpacity>
        </View>
        {loadingTVShows ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#007AFF" />
          </View>
        ) : recentTVShows.length > 0 ? (
          <FlatList
            data={recentTVShows}
            renderItem={renderTVShowCard}
            keyExtractor={(item) => item.id}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.rowContent}
            ItemSeparatorComponent={() => <View style={{ width: 12 }} />}
          />
        ) : (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No recent TV shows</Text>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 20,
    paddingTop: 60, // Account for status bar
  },
  menuButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#333333',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  menuButtonText: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: 'bold',
  },
  headerContent: {
    flex: 1,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 4,
  },
  serverText: {
    fontSize: 13,
    color: '#999999',
  },
  logoutButton: {
    backgroundColor: '#333333',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  logoutButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
  },
  section: {
    marginBottom: 32,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  seeAllText: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
  },
  loadingContainer: {
    height: POSTER_WIDTH * 1.5 + 40, // Poster height + meta height
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  emptyContainer: {
    height: 100,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  emptyText: {
    fontSize: 14,
    color: '#666666',
    fontStyle: 'italic',
  },
  rowContent: {
    paddingHorizontal: 20,
  },
  posterCard: {
    width: POSTER_WIDTH,
  },
  posterContainer: {
    width: POSTER_WIDTH,
    aspectRatio: 2 / 3,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: '#1a1a1a',
    marginBottom: 8,
  },
  poster: {
    width: '100%',
    height: '100%',
  },
  posterPlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  posterPlaceholderText: {
    fontSize: 40,
  },
  posterMeta: {
    paddingHorizontal: 4,
  },
  posterTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 2,
    lineHeight: 16,
  },
  posterYear: {
    fontSize: 11,
    color: '#999999',
  },
});
