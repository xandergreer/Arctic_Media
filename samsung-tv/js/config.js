// Configuration and Storage
const Config = {
    STORAGE_KEY_SERVER: 'arctic_server_url',
    STORAGE_KEY_ACCESS_TOKEN: 'arctic_access_token',
    STORAGE_KEY_REFRESH_TOKEN: 'arctic_refresh_token',
    
    // Default server URL (can be overridden)
    defaultServerUrl: '',
    
    // Get server URL from storage or default
    getServerUrl() {
        const stored = localStorage.getItem(this.STORAGE_KEY_SERVER);
        return stored || this.defaultServerUrl;
    },
    
    // Save server URL
    setServerUrl(url) {
        localStorage.setItem(this.STORAGE_KEY_SERVER, url);
    },
    
    // Get access token
    getAccessToken() {
        return localStorage.getItem(this.STORAGE_KEY_ACCESS_TOKEN);
    },
    
    // Save tokens
    setTokens(accessToken, refreshToken) {
        localStorage.setItem(this.STORAGE_KEY_ACCESS_TOKEN, accessToken);
        if (refreshToken) {
            localStorage.setItem(this.STORAGE_KEY_REFRESH_TOKEN, refreshToken);
        }
    },
    
    // Clear all stored data
    clear() {
        localStorage.removeItem(this.STORAGE_KEY_SERVER);
        localStorage.removeItem(this.STORAGE_KEY_ACCESS_TOKEN);
        localStorage.removeItem(this.STORAGE_KEY_REFRESH_TOKEN);
    },
    
    // Check if we have a server URL
    hasServerUrl() {
        return !!this.getServerUrl();
    },
    
    // Check if we have tokens
    hasTokens() {
        return !!this.getAccessToken();
    }
};

