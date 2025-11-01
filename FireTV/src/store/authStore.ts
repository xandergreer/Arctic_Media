import { create } from 'zustand';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthState, User, LoginCredentials, ServerConfig } from '../types';

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

// Helper function to log timeout diagnostics
const logTimeoutDiagnostics = (url: string) => {
  console.error('Diagnostics:');
  console.error(`- URL attempted: ${url}`);
  console.error(`- Timeout after: 15000ms`);
  console.error('- This could indicate:');
  console.error('  • Server is down or unreachable');
  console.error('  • Network connectivity issues');
  console.error('  • Firewall blocking the connection');
  console.error('  • DNS resolution problems (for domains)');
  console.error('  • iOS Simulator network configuration issues');
  console.error('  • Device and server on different networks');
  console.error('Try:');
  console.error('  • Test in a browser: open the URL in Safari/Chrome on the device');
  console.error('  • Check if server is accessible from another device');
  console.error('  • Verify server is running and listening on the correct port');
  console.error('  • For domains: check DNS is resolving correctly');
};

const saveServerConfig = async (config: ServerConfig) => {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch (error) {
    console.error('Failed to save server config:', error);
  }
};

const loadServerConfig = async (): Promise<ServerConfig | null> => {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
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
      await AsyncStorage.multiRemove([STORAGE_KEY, 'auth_token']);
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
      let isIPAddress = false;
      
      // Check if it's an IP address
      if (cleanUrl.match(/^(\d+\.\d+\.\d+\.\d+)/)) {
        isIPAddress = true;
      }
      
      // Extract domain/IP without protocol
      let urlWithoutProtocol = cleanUrl.replace(/^https?:\/\//, '');
      
      if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
        // Try HTTPS first for domains, HTTP for IP addresses
        if (isIPAddress) {
          cleanUrl = `http://${cleanUrl}`;
        } else {
          // For domains, try HTTPS first (most domains use HTTPS)
          cleanUrl = `https://${cleanUrl}`;
        }
      } else if (cleanUrl.startsWith('http://') && !isIPAddress) {
        // If user entered http:// for a domain, prefer HTTPS but try HTTP as fallback
        // We'll try HTTPS first in the connection logic below
        cleanUrl = `https://${urlWithoutProtocol}`;
      }

      // Remove trailing slash
      cleanUrl = cleanUrl.replace(/\/$/, '');

      console.log(`Attempting to connect to server at: ${cleanUrl}/health`);
      console.log(`Using React Native fetch API`);
      
      // Test the connection by trying to reach the server
      // Health endpoint is at root level, not under /api
      // Try using React Native's fetch first (better compatibility)
      const startTime = Date.now();
      
      // Create an AbortController for timeout (shorter timeout for initial test)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('Request timeout - aborting connection attempt');
        controller.abort();
      }, 10000); // Reduced to 10 seconds for faster feedback
      
      try {
        const fetchResponse = await fetch(`${cleanUrl}/health`, {
          method: 'GET',
          headers: {
            'User-Agent': 'ArcticMedia-iOS/1.0.0',
            'Accept': 'application/json',
          },
          signal: controller.signal,
        });
        
        clearTimeout(timeoutId);
        const duration = Date.now() - startTime;
        console.log(`Connection successful in ${duration}ms`);

        if (fetchResponse.ok) {
          const data = await fetchResponse.json();
          console.log('Health check response:', data);
          const config: ServerConfig = {
            url: cleanUrl,
            apiBase: `${cleanUrl}/api`,
            isValid: true
          };
          await get().setServerConfig(config);
          return true;
        } else {
          console.warn(`Health check returned status ${fetchResponse.status}`);
          return false;
        }
      } catch (firstError) {
        clearTimeout(timeoutId);
        console.error('Fetch failed, error:', firstError);
        
        // If HTTPS failed for a domain, try HTTP as fallback
        if (cleanUrl.startsWith('https://') && !cleanUrl.match(/^https?:\/\/(\d+\.){3}\d+/)) {
          const httpUrl = cleanUrl.replace('https://', 'http://');
          console.log(`HTTPS failed, trying HTTP: ${httpUrl}/health`);
          
          // Try HTTP with fetch first
          const httpController = new AbortController();
          const httpTimeoutId = setTimeout(() => {
            console.log('HTTP fallback timeout - aborting');
            httpController.abort();
          }, 10000);
          
          try {
            const httpResponse = await fetch(`${httpUrl}/health`, {
              method: 'GET',
              headers: {
                'User-Agent': 'ArcticMedia-iOS/1.0.0',
                'Accept': 'application/json',
              },
              signal: httpController.signal,
            });
            
            clearTimeout(httpTimeoutId);
            
            if (httpResponse.ok) {
              const data = await httpResponse.json();
              console.log('HTTP fallback successful, response:', data);
              const config: ServerConfig = {
                url: httpUrl,
                apiBase: `${httpUrl}/api`,
                isValid: true
              };
              await get().setServerConfig(config);
              return true;
            }
          } catch (httpError) {
            clearTimeout(httpTimeoutId);
            // Both fetch attempts failed, throw original error
            throw firstError;
          }
        } else {
          throw firstError;
        }
      }
      return false;
    } catch (error: any) {
      console.error('Server validation error:', error);
      // Return more detailed error info for debugging
      // Check if it's a fetch AbortError (timeout) or network error
      if (error.name === 'AbortError' || error.message?.includes('timeout') || error.message?.includes('aborted')) {
        console.error('Request was aborted (timeout)');
        logTimeoutDiagnostics(cleanUrl);
      } else if (error.message) {
        console.error('Error message:', error.message);
      }
      
      // Also check axios errors if axios was used somewhere
      if (axios.isAxiosError && axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
          console.error('Connection refused - server may not be running or URL is incorrect');
        } else if (error.code === 'ETIMEDOUT' || error.message?.includes('timeout')) {
          console.error('Connection timeout - server may be unreachable or network is slow');
          logTimeoutDiagnostics(cleanUrl);
        } else if (error.response) {
          console.error('Server responded with status:', error.response.status);
        } else if (error.request) {
          console.error('No response received from server - check network connection');
        }
      } else {
        console.error('Unexpected error:', error);
      }
      return false;
    }
  },

  login: async (credentials: LoginCredentials) => {
    try {
      set({ isLoading: true });
      const { serverConfig } = get();
      if (!serverConfig) {
        throw new Error('Server not configured');
      }

      // Direct API call to avoid circular dependency
      // Auth endpoints are at /auth, not /api/auth
      const api = axios.create({
        baseURL: serverConfig.url,
        timeout: 10000,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });

      const response = await api.post('/auth/login', credentials);
      const { user, token } = response.data;

      // Store token for future requests
      if (token) {
        await AsyncStorage.setItem('auth_token', token);
      }

      set({
        user,
        token: token || null,
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
      const { serverConfig, token } = get();
      if (serverConfig) {
        // Direct API call to avoid circular dependency
        // Auth endpoints are at /auth, not /api/auth
        const api = axios.create({
          baseURL: serverConfig.url,
          timeout: 10000,
          headers: {
            'Accept': 'application/json',
          },
        });

        // Add auth token to request
        if (token) {
          api.defaults.headers.Authorization = `Bearer ${token}`;
        }

        await api.post('/auth/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });

      // Clear token from AsyncStorage
      try {
        await AsyncStorage.removeItem('auth_token');
      } catch (error) {
        console.error('Failed to remove auth token:', error);
      }
    }
  },

  checkAuth: async () => {
    try {
      set({ isLoading: true });
      const { serverConfig } = get();
      if (!serverConfig) {
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
        return;
      }

      // Get token from AsyncStorage
      const token = await AsyncStorage.getItem('auth_token');

      if (!token) {
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
        return;
      }

      // Direct API call to avoid circular dependency
      // Auth endpoints are at /auth, not /api/auth
      const api = axios.create({
        baseURL: serverConfig.url,
        timeout: 10000,
        headers: {
          'Accept': 'application/json',
        },
      });

      // Add auth token to request
      api.defaults.headers.Authorization = `Bearer ${token}`;

      const response = await api.get('/auth/me');
      const user = response.data;

      if (user) {
        set({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    } catch (error) {
      console.error('Check auth error:', error);
      // On error, clear invalid token
      try {
        await AsyncStorage.removeItem('auth_token');
      } catch (storageError) {
        console.error('Failed to remove invalid token:', storageError);
      }
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
