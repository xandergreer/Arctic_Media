import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { GridDensity } from '../components/OptionsMenu';

interface PreferencesStore {
  movieDensity: GridDensity;
  tvShowDensity: GridDensity;
  seasonDensity: GridDensity;
  episodeDensity: GridDensity;
  setMovieDensity: (density: GridDensity) => void;
  setTVShowDensity: (density: GridDensity) => void;
  setSeasonDensity: (density: GridDensity) => void;
  setEpisodeDensity: (density: GridDensity) => void;
  loadPreferences: () => Promise<void>;
}

const STORAGE_KEYS = {
  movies: 'arctic_media_movies_density',
  tvShows: 'arctic_media_tvshows_density',
  seasons: 'arctic_media_seasons_density',
  episodes: 'arctic_media_episodes_density',
};

const DEFAULT_DENSITY: GridDensity = 2;

const savePreference = async (key: string, density: GridDensity) => {
  try {
    await AsyncStorage.setItem(key, density.toString());
  } catch (error) {
    console.error('Failed to save preference:', error);
  }
};

const loadPreference = async (key: string): Promise<GridDensity> => {
  try {
    const stored = await AsyncStorage.getItem(key);
    if (stored) {
      const density = parseInt(stored, 10);
      if (density === 2 || density === 3 || density === 4) {
        return density as GridDensity;
      }
    }
  } catch (error) {
    console.error('Failed to load preference:', error);
  }
  return DEFAULT_DENSITY;
};

export const usePreferencesStore = create<PreferencesStore>((set, get) => ({
  movieDensity: DEFAULT_DENSITY,
  tvShowDensity: DEFAULT_DENSITY,
  seasonDensity: DEFAULT_DENSITY,
  episodeDensity: DEFAULT_DENSITY,

  setMovieDensity: async (density: GridDensity) => {
    set({ movieDensity: density });
    await savePreference(STORAGE_KEYS.movies, density);
  },

  setTVShowDensity: async (density: GridDensity) => {
    set({ tvShowDensity: density });
    await savePreference(STORAGE_KEYS.tvShows, density);
  },

  setSeasonDensity: async (density: GridDensity) => {
    set({ seasonDensity: density });
    await savePreference(STORAGE_KEYS.seasons, density);
  },

  setEpisodeDensity: async (density: GridDensity) => {
    set({ episodeDensity: density });
    await savePreference(STORAGE_KEYS.episodes, density);
  },

  loadPreferences: async () => {
    try {
      const [movies, tvShows, seasons, episodes] = await Promise.all([
        loadPreference(STORAGE_KEYS.movies),
        loadPreference(STORAGE_KEYS.tvShows),
        loadPreference(STORAGE_KEYS.seasons),
        loadPreference(STORAGE_KEYS.episodes),
      ]);
      
      set({
        movieDensity: movies,
        tvShowDensity: tvShows,
        seasonDensity: seasons,
        episodeDensity: episodes,
      });
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  },
}));
