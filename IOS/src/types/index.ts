// TypeScript interfaces for Arctic Media app

export interface ServerConfig {
  url: string;
  apiBase: string;
  isValid: boolean;
}

export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  created_at: string;
}

export interface MediaItem {
  id: string;
  kind: string;
  title: string;
  year?: number;
  poster_url?: string;
  backdrop_url?: string;
  overview?: string;
  runtime_ms?: number;
}

export interface TVShow extends MediaItem {
  first_air_date?: string;
  seasons?: number;
  episodes?: number;
}

export interface Season {
  id: string;
  title: string;
  season: number;
}

export interface Episode {
  id: string;
  title: string;
  still?: string;
  air_date?: string;
  episode?: number;
  first_file_id?: string;
}

export interface Library {
  id: string;
  name: string;
  slug: string;
  type: string;
  path: string;
  created_at: string;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  serverConfig: ServerConfig | null;
}
