import axios from 'axios';
import { MediaItem, TVShow, Season, Episode, Library } from '../types';
import { useAuthStore } from '../store/authStore';

// Create axios instance with dynamic configuration
const createApiInstance = () => {
  const { serverConfig } = useAuthStore.getState();

  if (!serverConfig) {
    throw new Error('Server not configured');
  }

  const api = axios.create({
    baseURL: serverConfig.apiBase,
    timeout: 10000,
  });

  // Add request interceptor to include auth token
  api.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return api;
};

export const mediaAPI = {
  // Get all TV shows
  async getShows(): Promise<TVShow[]> {
    try {
      const api = createApiInstance();
      const response = await api.get('/tv/shows');
      return response.data;
    } catch (error) {
      console.error('Get shows error:', error);
      throw new Error('Failed to fetch TV shows.');
    }
  },

  // Get seasons for a specific show
  async getSeasons(showId: string): Promise<Season[]> {
    try {
      const api = createApiInstance();
      const response = await api.get(`/tv/seasons?show_id=${showId}`);
      return response.data;
    } catch (error) {
      console.error('Get seasons error:', error);
      throw new Error('Failed to fetch seasons.');
    }
  },

  // Get episodes for a specific season
  async getEpisodes(showId: string, season: number): Promise<Episode[]> {
    try {
      const api = createApiInstance();
      const response = await api.get(`/tv/episodes?show_id=${showId}&season=${season}`);
      return response.data;
    } catch (error) {
      console.error('Get episodes error:', error);
      throw new Error('Failed to fetch episodes.');
    }
  },

  // Get all libraries
  async getLibraries(): Promise<Library[]> {
    try {
      const api = createApiInstance();
      const response = await api.get('/libraries');
      return response.data;
    } catch (error) {
      console.error('Get libraries error:', error);
      throw new Error('Failed to fetch libraries.');
    }
  },

  // Get movies from a library
  async getMovies(libraryId: string): Promise<MediaItem[]> {
    try {
      const api = createApiInstance();
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
  }
};
