// API Client for Arctic Media Server
const API = {
    // Get base URL
    getBaseUrl() {
        return Config.getServerUrl();
    },
    
    // Get API base URL
    getApiUrl() {
        const base = this.getBaseUrl();
        return base ? `${base}/api` : '';
    },
    
    // Make authenticated request
    async request(endpoint, options = {}) {
        const apiUrl = this.getApiUrl();
        if (!apiUrl) {
            throw new Error('Server URL not configured');
        }
        
        const url = `${apiUrl}${endpoint}`;
        const token = Config.getAccessToken();
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Token expired, try to refresh
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry with new token
                    headers['Authorization'] = `Bearer ${Config.getAccessToken()}`;
                    const retryResponse = await fetch(url, { ...config, headers });
                    return this.handleResponse(retryResponse);
                } else {
                    // Refresh failed, clear tokens
                    Config.clear();
                    throw new Error('Authentication expired');
                }
            }
            
            return this.handleResponse(response);
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    // Handle response
    async handleResponse(response) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Request failed');
            }
            return data;
        }
        return await response.text();
    },
    
    // Refresh access token
    async refreshToken() {
        const refreshToken = localStorage.getItem(Config.STORAGE_KEY_REFRESH_TOKEN);
        if (!refreshToken) {
            return false;
        }
        
        try {
            const response = await fetch(`${this.getApiUrl()}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (response.ok) {
                const data = await response.json();
                Config.setTokens(data.access_token, data.refresh_token);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        
        return false;
    },
    
    // Test server connection
    async testConnection(serverUrl) {
        try {
            const response = await fetch(`${serverUrl}/health`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    },
    
    // Pairing: Request pairing code
    async requestPairing() {
        const baseUrl = this.getBaseUrl();
        const response = await fetch(`${baseUrl}/api/pair/request`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return this.handleResponse(response);
    },
    
    // Pairing: Poll for authorization
    async pollPairing(deviceCode) {
        const baseUrl = this.getBaseUrl();
        const response = await fetch(`${baseUrl}/api/pair/poll`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ device_code: deviceCode })
        });
        return this.handleResponse(response);
    },
    
    // Get TV shows
    async getShows() {
        return this.request('/tv/shows');
    },
    
    // Get seasons for a show
    async getSeasons(showId) {
        return this.request(`/tv/seasons?show_id=${encodeURIComponent(showId)}`);
    },
    
    // Get episodes for a season
    async getEpisodes(showId, season) {
        return this.request(`/tv/episodes?show_id=${encodeURIComponent(showId)}&season=${season}`);
    },
    
    // Get movies (if available)
    async getMovies() {
        // This endpoint might need to be implemented in the backend
        // For now, return empty array
        try {
            return this.request('/movies');
        } catch (error) {
            console.warn('Movies endpoint not available:', error);
            return [];
        }
    },
    
    // Get stream URL for a file/item
    // Can use either fileId or itemId - HLS endpoint accepts both
    getStreamUrl(fileOrItemId) {
        const baseUrl = this.getBaseUrl();
        const token = Config.getAccessToken();
        // Use item_id for HLS streaming (works with both item_id and file_id)
        // Token can be passed as query param or in Authorization header
        // HLS.js will handle headers, but we include token in URL as fallback
        return `${baseUrl}/stream/${encodeURIComponent(fileOrItemId)}/master.m3u8?token=${encodeURIComponent(token || '')}`;
    },
    
    // Get headers for authenticated requests (for HLS.js xhrSetup)
    getAuthHeaders() {
        const token = Config.getAccessToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }
};

