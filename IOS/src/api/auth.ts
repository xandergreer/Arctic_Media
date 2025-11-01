import axios from 'axios';
import { LoginCredentials, User, ServerConfig } from '../types';

// Create axios instance with dynamic configuration
const createApiInstance = (serverConfig: ServerConfig) => {
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
  async login(credentials: LoginCredentials, serverConfig: ServerConfig): Promise<User> {
    try {
      const api = createApiInstance(serverConfig);
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

  async logout(serverConfig: ServerConfig): Promise<void> {
    try {
      const api = createApiInstance(serverConfig);
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Remove token regardless of API call success
      localStorage.removeItem('auth_token');
    }
  },

  async getCurrentUser(serverConfig: ServerConfig): Promise<User | null> {
    try {
      const api = createApiInstance(serverConfig);
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error);
      return null;
    }
  }
};
