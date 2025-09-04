import axios from 'axios';
import { LoginCredentials, User } from '../types';
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

export const authAPI = {
  async login(credentials: LoginCredentials): Promise<User> {
    try {
      const api = createApiInstance();
      const response = await api.post('/auth/login', credentials);
      const { user, token } = response.data;

      // Store token for future requests
      if (token) {
        localStorage.setItem('auth_token', token);
      }

      return user;
    } catch (error) {
      console.error('Login error:', error);
      throw new Error('Login failed. Please check your credentials.');
    }
  },

  async logout(): Promise<void> {
    try {
      const api = createApiInstance();
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Remove token regardless of API call success
      localStorage.removeItem('auth_token');
    }
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const api = createApiInstance();
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error);
      return null;
    }
  }
};
