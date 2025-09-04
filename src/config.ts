// Configuration for Arctic Media app
export const CONFIG = {
  // Update this to match your Arctic Media server IP and port
  SERVER_URL: 'http://192.168.1.100:8000',
  API_BASE: 'http://192.168.1.100:8000/api',

  // App settings
  APP_NAME: 'Arctic Media',
  VERSION: '1.0.0',

  // UI settings
  THEME: {
    primary: '#007AFF',
    secondary: '#5856D6',
    success: '#34C759',
    warning: '#FF9500',
    error: '#FF3B30',
    background: '#000000',
    surface: '#1a1a1a',
    text: '#ffffff',
    textSecondary: '#cccccc',
    textTertiary: '#999999',
  },

  // Streaming settings
  STREAMING: {
    preferHLS: true,
    timeout: 10000,
    retryAttempts: 3,
  },
};

// Helper function to get full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${CONFIG.API_BASE}${endpoint}`;
};

// Helper function to get streaming URL
export const getStreamingUrl = (itemId: string): string => {
  return `${CONFIG.SERVER_URL}/stream/${itemId}/file`;
};

// Helper function to get HLS streaming URL
export const getHLSStreamingUrl = (itemId: string): string => {
  return `${CONFIG.SERVER_URL}/stream/${itemId}/master.m3u8`;
};
