import { create } from 'zustand';
import { AuthState, User, LoginCredentials, ServerConfig } from '../types';
import { authAPI } from '../api/auth';

interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  setServerConfig: (config: ServerConfig) => void;
  validateServer: (url: string) => Promise<boolean>;
  clearServerConfig: () => void;
  loadPersistedConfig: () => Promise<void>;
}

// Simple persistence for server config
const STORAGE_KEY = 'arctic_media_server_config';

const saveServerConfig = async (config: ServerConfig) => {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    }
  } catch (error) {
    console.error('Failed to save server config:', error);
  }
};

const loadServerConfig = async (): Promise<ServerConfig | null> => {
  try {
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    }
    return null;
  } catch (error) {
    console.error('Failed to load server config:', error);
    return null;
  }
};

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  serverConfig: null,

  setLoading: (loading: boolean) => set({ isLoading: loading }),

  setServerConfig: async (config: ServerConfig) => {
    set({ serverConfig: config });
    await saveServerConfig(config);
  },

  clearServerConfig: async () => {
    set({ serverConfig: null, user: null, token: null, isAuthenticated: false });
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem('auth_token');
      }
    } catch (error) {
      console.error('Failed to clear stored data:', error);
    }
  },

  loadPersistedConfig: async () => {
    try {
      const config = await loadServerConfig();
      if (config) {
        set({ serverConfig: config });
      }
    } catch (error) {
      console.error('Failed to load persisted config:', error);
    }
  },

  validateServer: async (url: string): Promise<boolean> => {
    try {
      // Clean up the URL
      let cleanUrl = url.trim();
      if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
        cleanUrl = `http://${cleanUrl}`;
      }

      // Remove trailing slash
      cleanUrl = cleanUrl.replace(/\/$/, '');

      // Test the connection by trying to reach the server
      const response = await fetch(`${cleanUrl}/api/health`, {
        method: 'GET',
        timeout: 5000
      });

      if (response.ok) {
        const config: ServerConfig = {
          url: cleanUrl,
          apiBase: `${cleanUrl}/api`,
          isValid: true
        };
        await get().setServerConfig(config);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Server validation error:', error);
      return false;
    }
  },

  login: async (credentials: LoginCredentials) => {
    try {
      set({ isLoading: true });
      const user = await authAPI.login(credentials);
      set({
        user,
        token: localStorage.getItem('auth_token'),
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  checkAuth: async () => {
    try {
      set({ isLoading: true });
      const user = await authAPI.getCurrentUser();
      if (user) {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
