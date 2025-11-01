import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MediaItem, TVShow, Season, Episode, Library } from '../types';
import { useAuthStore } from '../store/authStore';

// Create axios instance with dynamic configuration
const createApiInstance = async () => {
  const { serverConfig, token } = useAuthStore.getState();

  if (!serverConfig) {
    throw new Error('Server not configured');
  }

  const api = axios.create({
    baseURL: serverConfig.apiBase,
    timeout: 10000,
  });

  // Add request interceptor to include auth token
  api.interceptors.request.use(async (config) => {
    // Use token from store, or fetch from AsyncStorage if not available
    const authToken = token || await AsyncStorage.getItem('auth_token');
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  });

  return api;
};

export const mediaAPI = {
  // Get all TV shows
  async getShows(): Promise<TVShow[]> {
    try {
      const api = await createApiInstance();
      // Use /tv endpoint instead of /tv/shows to get full extra_json
      const response = await api.get('/tv?page=1&page_size=1000');
      // Map backend response fields to app types
      // Backend returns 'poster' but app expects 'poster_url'
      const { serverConfig } = useAuthStore.getState();
      return (response.data.items || []).map((show: any) => {
        const ej = show.extra_json || {};
        // Convert relative poster URLs to absolute URLs
        let posterUrl = ej.poster || show.poster_url;
        if (posterUrl && !posterUrl.startsWith('http')) {
          // If it's a relative URL, make it absolute
          posterUrl = posterUrl.startsWith('/') 
            ? `${serverConfig?.url || ''}${posterUrl}`
            : `${serverConfig?.url || ''}/${posterUrl}`;
        }
        
        let backdropUrl = ej.backdrop || show.backdrop_url;
        if (backdropUrl && !backdropUrl.startsWith('http')) {
          backdropUrl = backdropUrl.startsWith('/')
            ? `${serverConfig?.url || ''}${backdropUrl}`
            : `${serverConfig?.url || ''}/${backdropUrl}`;
        }
        
        return {
          ...show,
          poster_url: posterUrl,
          backdrop_url: backdropUrl,
          extra_json: ej, // Include full extra_json for metadata
        };
      });
    } catch (error) {
      console.error('Get shows error:', error);
      throw new Error('Failed to fetch TV shows.');
    }
  },

  // Get seasons for a specific show
  async getSeasons(showId: string): Promise<Season[]> {
    try {
      const api = await createApiInstance();
      const response = await api.get(`/tv/seasons?show_id=${showId}`);
      const { serverConfig } = useAuthStore.getState();
      // Map seasons and add poster URLs - seasons API doesn't return poster_url, so we'll use placeholder or show poster
      return response.data.map((season: any) => {
        // Seasons don't have poster_url in the API response, so we'll set it to null
        // The UI will use show poster as fallback
        return {
          ...season,
          poster_url: null, // Will use show poster or placeholder in UI
        };
      });
    } catch (error) {
      console.error('Get seasons error:', error);
      throw new Error('Failed to fetch seasons.');
    }
  },

  // Get episodes for a specific season
  async getEpisodes(showId: string, season: number): Promise<Episode[]> {
    try {
      const api = await createApiInstance();
      const response = await api.get(`/tv/episodes?show_id=${showId}&season=${season}`);
      // Map backend response fields and convert relative URLs to absolute
      const { serverConfig } = useAuthStore.getState();
      return response.data.map((episode: any) => {
        // Handle episode still URL
        // Still URLs from TMDB are already absolute (https://image.tmdb.org/...)
        // Backend now provides fallback (season/show poster) if episode still is missing
        let stillUrl = episode.still;
        
        // Debug: Log what we receive from backend
        console.log(`Episode ${episode.episode || episode.id} raw still from backend:`, {
          still: episode.still,
          stillType: typeof episode.still,
          stillIsNull: episode.still === null,
          stillIsUndefined: episode.still === undefined,
        });
        
        if (stillUrl && typeof stillUrl === 'string' && stillUrl.trim() !== '') {
          // If it's already a full URL (TMDB or other), use it as-is
          if (stillUrl.startsWith('http://') || stillUrl.startsWith('https://')) {
            // Already absolute, keep it
          } else if (stillUrl.startsWith('/')) {
            // Relative URL starting with / - make it absolute
            stillUrl = `${serverConfig?.url || ''}${stillUrl}`;
          } else {
            // Relative URL without / - make it absolute
            stillUrl = `${serverConfig?.url || ''}/${stillUrl}`;
          }
          console.log(`Episode ${episode.episode || episode.id} processed still URL:`, stillUrl);
        } else {
          console.warn(`Episode ${episode.episode || episode.id} has no valid still URL`);
          stillUrl = undefined;
        }
        
        return {
          ...episode,
          still: stillUrl,
        };
      });
    } catch (error) {
      console.error('Get episodes error:', error);
      throw new Error('Failed to fetch episodes.');
    }
  },

  // Get all libraries
  async getLibraries(): Promise<Library[]> {
    try {
      const { serverConfig } = useAuthStore.getState();
      if (!serverConfig) {
        throw new Error('Server not configured');
      }
      
      // The libraries router is included without /api prefix in main.py
      // So the endpoint is /libraries (not /api/libraries)
      // Get token from store or AsyncStorage
      const token = useAuthStore.getState().token || await AsyncStorage.getItem('auth_token');
      
      if (!token) {
        throw new Error('Not authenticated - no token available');
      }
      
      // Libraries endpoint - use Bearer token auth
      const response = await axios.get(`${serverConfig.url}/libraries`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        timeout: 10000,
      });
      
      console.log('Libraries fetched successfully:', response.data?.length || 0, 'libraries');
      return response.data || [];
    } catch (error: any) {
      console.error('Get libraries error:', error);
      if (error.response) {
        console.error('Libraries API error response:', {
          status: error.response.status,
          data: error.response.data,
          url: error.config?.url,
        });
      }
      return []; // Return empty array instead of throwing
    }
  },

  // Get movies from a library
  async getMovies(libraryId: string): Promise<MediaItem[]> {
    try {
      const api = await createApiInstance();
      const response = await api.get(`/libraries/${libraryId}/items?type=movie`);
      return response.data;
    } catch (error) {
      console.error('Get movies error:', error);
      throw new Error('Failed to fetch movies.');
    }
  },

  // Get streaming URL for a media item
  getStreamingUrl(itemId: string): string {
    const { serverConfig } = useAuthStore.getState();
    if (!serverConfig) {
      throw new Error('Server not configured');
    }
    return `${serverConfig.url}/stream/${itemId}/file`;
  },

  // Get HLS streaming URL for a media item
  getHLSStreamingUrl(itemId: string): string {
    const { serverConfig } = useAuthStore.getState();
    if (!serverConfig) {
      throw new Error('Server not configured');
    }
    return `${serverConfig.url}/stream/${itemId}/master.m3u8`;
  },

  // Get media item files
  async getMediaFiles(mediaId: string): Promise<any[]> {
    try {
      const api = await createApiInstance();
      const filesResponse = await api.get(`/media/${mediaId}/files`);
      return filesResponse.data || [];
    } catch (error) {
      console.error('Get media files error:', error);
      return [];
    }
  },

  // Get show details with all metadata
  async getShowDetail(showId: string): Promise<any> {
    try {
      // We'll need to get this from the show detail page
      // For now, return the show from the shows list
      const shows = await this.getShows();
      const show = shows.find(s => s.id === showId);
      if (!show) {
        throw new Error('Show not found');
      }
      return show;
    } catch (error) {
      console.error('Get show detail error:', error);
      throw new Error('Failed to fetch show details.');
    }
  },

  // Get recent movies
  async getRecentMovies(limit: number = 20): Promise<MediaItem[]> {
    try {
      const api = await createApiInstance();
      const response = await api.get(`/movies?sort=recent&page=1&page_size=${limit}`);
      const { serverConfig } = useAuthStore.getState();
      return (response.data.items || []).map((movie: any) => {
        const ej = movie.extra_json || {};
        let posterUrl = ej.poster || movie.poster_url;
        if (posterUrl && !posterUrl.startsWith('http')) {
          posterUrl = posterUrl.startsWith('/') 
            ? `${serverConfig?.url || ''}${posterUrl}`
            : `${serverConfig?.url || ''}/${posterUrl}`;
        }
        let backdropUrl = ej.backdrop || movie.backdrop_url;
        if (backdropUrl && !backdropUrl.startsWith('http')) {
          backdropUrl = backdropUrl.startsWith('/')
            ? `${serverConfig?.url || ''}${backdropUrl}`
            : `${serverConfig?.url || ''}/${backdropUrl}`;
        }
        return {
          ...movie,
          poster_url: posterUrl,
          backdrop_url: backdropUrl,
          extra_json: ej, // Include full extra_json for metadata
        };
      });
    } catch (error) {
      console.error('Get recent movies error:', error);
      throw new Error('Failed to fetch recent movies.');
    }
  },

  // Get recent TV shows
  async getRecentTVShows(limit: number = 20): Promise<TVShow[]> {
    try {
      const api = await createApiInstance();
      const response = await api.get(`/tv?sort=recent&page=1&page_size=${limit}`);
      const { serverConfig } = useAuthStore.getState();
      return (response.data.items || []).map((show: any) => {
        const ej = show.extra_json || {};
        let posterUrl = ej.poster || show.poster_url;
        if (posterUrl && !posterUrl.startsWith('http')) {
          posterUrl = posterUrl.startsWith('/') 
            ? `${serverConfig?.url || ''}${posterUrl}`
            : `${serverConfig?.url || ''}/${posterUrl}`;
        }
        let backdropUrl = ej.backdrop || show.backdrop_url;
        if (backdropUrl && !backdropUrl.startsWith('http')) {
          backdropUrl = backdropUrl.startsWith('/')
            ? `${serverConfig?.url || ''}${backdropUrl}`
            : `${serverConfig?.url || ''}/${backdropUrl}`;
        }
        return {
          ...show,
          poster_url: posterUrl,
          backdrop_url: backdropUrl,
          extra_json: ej, // Include full extra_json for metadata
        };
      });
    } catch (error) {
      console.error('Get recent TV shows error:', error);
      throw new Error('Failed to fetch recent TV shows.');
    }
  },
};
