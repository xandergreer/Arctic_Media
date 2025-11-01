import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import { useNavigation } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { VideoView, useVideoPlayer } from 'expo-video';

type PlayerScreenRouteProp = RouteProp<RootStackParamList, 'Player'>;

export default function PlayerScreen() {
  const route = useRoute<PlayerScreenRouteProp>();
  const navigation = useNavigation();
  const { itemId, title } = route.params;

  const [streamingUrl, setStreamingUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Setup streaming URL
  const setupStreaming = () => {
    try {
      setLoading(true);
      setError(null);
      // Try HLS streaming first (better for mobile)
      const hlsUrl = mediaAPI.getHLSStreamingUrl(itemId);
      setStreamingUrl(hlsUrl);
      setLoading(false);
    } catch (err) {
      setError('Failed to setup streaming');
      setLoading(false);
    }
  };

  useEffect(() => {
    setupStreaming();
  }, [itemId]);

  // Note: We don't manually lock orientation anymore
  // The native controls handle fullscreen rotation automatically
  // Manual locking was causing conflicts with playback controls

  // Create video player with expo-video
  // Note: useVideoPlayer hook recreates player when source changes
  const player = useVideoPlayer(streamingUrl || '', (player) => {
    player.loop = false;
  });

  // Auto-play when URL is ready
  useEffect(() => {
    if (streamingUrl && player && !loading) {
      const timer = setTimeout(() => {
        if (player && !player.playing) {
          try {
            player.play();
          } catch (err) {
            console.error('Play error:', err);
          }
        }
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [streamingUrl, player, loading]);

  const handleBackPress = () => {
    navigation.goBack();
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading video...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={setupStreaming}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.backButton} onPress={handleBackPress}>
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!streamingUrl) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading video...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar hidden={true} />
      {streamingUrl && player ? (
        <VideoView
          player={player}
          style={styles.video}
          contentFit="contain"
          nativeControls={true}
          allowsFullscreen={true}
          allowsPictureInPicture={false}
        />
      ) : null}

      {/* Back button overlay - with pointer events disabled on container to avoid blocking native controls */}
      <View style={styles.backButtonContainer} pointerEvents="box-none">
        <TouchableOpacity style={styles.backButton} onPress={handleBackPress}>
          <Text style={styles.backButtonText}>‹ Back</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 18,
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
    marginBottom: 16,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  video: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  backButtonContainer: {
    position: 'absolute',
    top: 50,
    left: 20,
    zIndex: 1, // Behind native video controls
    elevation: 1,
  },
  backButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
