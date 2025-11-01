import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Dimensions,
} from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import { useNavigation } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/AppNavigator';
import { mediaAPI } from '../api/media';
import { VideoView, useVideoPlayer } from 'expo-video';

type PlayerScreenRouteProp = RouteProp<RootStackParamList, 'Player'>;

const { width, height } = Dimensions.get('window');

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
          player.play().catch((err) => {
            console.error('Play error:', err);
          });
        }
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [streamingUrl, player, loading]);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);


  // Track player status
  useEffect(() => {
    if (!player) return;

    const updateStatus = () => {
      setIsPlaying(player.playing);
      setCurrentTime(player.currentTime / 1000); // Convert to seconds
      setDuration(player.duration / 1000); // Convert to seconds
    };

    const subscription = player.addListener('statusChange', () => {
      updateStatus();
    });

    updateStatus(); // Initial update

    return () => {
      subscription?.remove();
    };
  }, [player]);

  const togglePlayPause = () => {
    if (player) {
      if (player.playing) {
        player.pause();
      } else {
        player.play();
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleBackPress = () => {
    navigation.goBack();
  };

  const handleVideoTap = () => {
    setShowControls(!showControls);
  };

  const handleSeek = (position: number) => {
    if (player) {
      player.currentTime = position * 1000; // Convert to milliseconds
    }
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
      <View style={styles.videoContainer}>
        {streamingUrl && player ? (
          <VideoView
            player={player}
            style={styles.video}
            contentFit="contain"
            nativeControls={true}
            allowsFullscreen={true}
          />
        ) : null}
      </View>

      {/* Back button always visible */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.backButton} onPress={handleBackPress}>
          <Text style={styles.backButtonText}>‹ Back</Text>
        </TouchableOpacity>
      </View>

      {/* Custom controls - not needed when using native controls */}
      {false && (
        <>
          <View style={styles.playbackControlsOverlay}>
            <TouchableOpacity style={styles.playButton} onPress={togglePlayPause}>
              <Text style={styles.playButtonText}>
                {isPlaying ? '⏸' : '▶'}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.bottomControls}>
            <View style={styles.titleContainer}>
              <Text style={styles.titleText}>{title}</Text>
            </View>
            
            <View style={styles.progressContainer}>
              <Text style={styles.timeText}>
                {formatTime(currentTime)} / {formatTime(duration)}
              </Text>
              {duration > 0 && (
                <View style={styles.seekBarContainer}>
                  <View style={styles.seekBarBackground}>
                    <View 
                      style={[
                        styles.seekBarProgress, 
                        { width: `${(currentTime / duration) * 100}%` }
                      ]} 
                    />
                  </View>
                </View>
              )}
            </View>
          </View>
        </>
      )}
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
  videoContainer: {
    width: width,
    height: height,
    justifyContent: 'center',
    alignItems: 'center',
  },
  video: {
    width: width,
    height: height,
  },
  controls: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    padding: 20,
    paddingTop: 50, // Safe area for status bar
    flexDirection: 'row',
    zIndex: 100, // Always on top
  },
  playbackControlsOverlay: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -30 }, { translateY: -30 }],
    zIndex: 10,
  },
  bottomControls: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  backButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  playbackControls: {
    flex: 1,
    alignItems: 'center',
  },
  playButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButtonText: {
    fontSize: 24,
    color: '#ffffff',
  },
  progressContainer: {
    padding: 20,
    alignItems: 'center',
    width: '100%',
  },
  timeText: {
    color: '#ffffff',
    fontSize: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    marginBottom: 12,
  },
  seekBarContainer: {
    width: '100%',
    paddingHorizontal: 20,
  },
  seekBarBackground: {
    width: '100%',
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  seekBarProgress: {
    height: '100%',
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  titleContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
  },
  titleText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    textAlign: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
});
