// Main Application Logic
const App = {
    currentScreen: 'loading',
    pairingInterval: null,
    pairingDeviceCode: null,
    
    // Initialize app
    async init() {
        console.log('Arctic Media App: Initializing...');
        
        // Initialize navigation
        Navigation.init();
        
        // Check if we have server URL and tokens
        const hasServer = Config.hasServerUrl();
        const hasTokens = Config.hasTokens();
        
        if (!hasServer) {
            this.showScreen('server-config');
        } else if (!hasTokens) {
            this.startPairing();
        } else {
            this.showScreen('main');
            await this.loadContent();
        }
        
        // Hide loading screen
        this.hideLoading();
    },
    
    // Hide loading screen
    hideLoading() {
        document.getElementById('loading-screen').classList.remove('active');
    },
    
    // Show screen
    showScreen(screenName) {
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        // Show requested screen
        const screen = document.getElementById(`${screenName}-screen`);
        if (screen) {
            screen.classList.add('active');
            this.currentScreen = screenName;
        }
        
        // Refresh navigation
        if (screenName === 'main') {
            setTimeout(() => Navigation.refresh(), 100);
        }
    },
    
    // Server Configuration
    setupServerConfig() {
        const input = document.getElementById('server-url-input');
        const connectBtn = document.getElementById('connect-btn');
        const errorMsg = document.getElementById('server-error');
        
        // Load existing server URL if available
        const existingUrl = Config.getServerUrl();
        if (existingUrl) {
            input.value = existingUrl;
        }
        
        // Connect button handler
        connectBtn.addEventListener('click', async () => {
            const url = input.value.trim();
            if (!url) {
                errorMsg.textContent = 'Please enter a server URL';
                errorMsg.classList.add('show');
                return;
            }
            
            // Normalize URL
            const normalizedUrl = url.replace(/\/$/, '');
            
            // Test connection
            errorMsg.textContent = 'Testing connection...';
            errorMsg.classList.add('show');
            
            const connected = await API.testConnection(normalizedUrl);
            
            if (connected) {
                Config.setServerUrl(normalizedUrl);
                errorMsg.classList.remove('show');
                this.startPairing();
            } else {
                errorMsg.textContent = 'Failed to connect. Please check the server URL.';
            }
        });
        
        // Enter key handler
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                connectBtn.click();
            }
        });
    },
    
    // Start pairing process
    async startPairing() {
        this.showScreen('pairing');
        
        try {
            // Request pairing code
            const pairing = await API.requestPairing();
            this.pairingDeviceCode = pairing.device_code;
            
            // Display pairing code
            const codeDisplay = document.getElementById('pairing-code');
            const code = pairing.user_code.match(/.{1,4}/g).join(' ');
            codeDisplay.textContent = code;
            
            // Display pairing URL
            const urlDisplay = document.getElementById('pairing-url');
            urlDisplay.textContent = pairing.server_url;
            
            // Start polling
            this.startPairingPoll();
            
            // Cancel button
            document.getElementById('pairing-cancel-btn').onclick = () => {
                this.stopPairingPoll();
                Config.clear();
                this.showScreen('server-config');
            };
            
        } catch (error) {
            console.error('Pairing request failed:', error);
            document.getElementById('pairing-status').textContent = 'Failed to start pairing. Please try again.';
        }
    },
    
    // Start polling for pairing authorization
    startPairingPoll() {
        if (this.pairingInterval) {
            clearInterval(this.pairingInterval);
        }
        
        this.pairingInterval = setInterval(async () => {
            try {
                const result = await API.pollPairing(this.pairingDeviceCode);
                
                if (result.status === 'authorized') {
                    // Save tokens
                    Config.setTokens(result.access_token, result.refresh_token);
                    
                    // Stop polling
                    this.stopPairingPoll();
                    
                    // Show main screen
                    this.showScreen('main');
                    await this.loadContent();
                } else if (result.status === 'expired') {
                    this.stopPairingPoll();
                    document.getElementById('pairing-status').textContent = 'Pairing code expired. Please try again.';
                }
            } catch (error) {
                console.error('Pairing poll failed:', error);
            }
        }, 3000); // Poll every 3 seconds
    },
    
    // Stop pairing poll
    stopPairingPoll() {
        if (this.pairingInterval) {
            clearInterval(this.pairingInterval);
            this.pairingInterval = null;
        }
    },
    
    // Load content for main screen
    async loadContent() {
        this.showLoadingMessage('Loading content...');
        
        try {
            // Load TV shows
            await this.loadTVShows();
            
            // Setup navigation
            this.setupNavigation();
            
            // Setup settings
            this.setupSettings();
            
            this.hideLoadingMessage();
        } catch (error) {
            console.error('Failed to load content:', error);
            this.hideLoadingMessage();
        }
    },
    
    // Load TV shows
    async loadTVShows() {
        try {
            const shows = await API.getShows();
            this.renderShows(shows);
        } catch (error) {
            console.error('Failed to load TV shows:', error);
            document.getElementById('tv-grid').innerHTML = '<p>Failed to load TV shows</p>';
        }
    },
    
    // Render TV shows
    renderShows(shows) {
        const grid = document.getElementById('tv-grid');
        grid.innerHTML = '';
        
        shows.forEach(show => {
            const card = document.createElement('div');
            card.className = 'content-card';
            card.tabIndex = 0;
            
            const poster = show.poster || '/static/img/placeholder.png';
            const year = show.first_air_date ? show.first_air_date.substring(0, 4) : '';
            
            card.innerHTML = `
                <img src="${poster}" alt="${show.title}" loading="lazy">
                <div class="card-info">
                    <div class="card-title">${show.title}</div>
                    <div class="card-subtitle">${year}</div>
                </div>
            `;
            
            card.onclick = () => this.showShowDetail(show);
            
            grid.appendChild(card);
        });
        
        Navigation.updateFocusableElements();
    },
    
    // Show show detail
    async showShowDetail(show) {
        Navigation.currentView = 'show-detail';
        
        // Hide all views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        
        // Show detail view
        const detailView = document.getElementById('show-detail-view');
        detailView.classList.add('active');
        
        const content = document.getElementById('show-detail-content');
        content.innerHTML = `
            <div class="show-detail-poster">
                <img src="${show.poster || '/static/img/placeholder.png'}" alt="${show.title}">
            </div>
            <div class="show-detail-info">
                <h3>${show.title}</h3>
                <p>Seasons: ${show.seasons || 'N/A'}</p>
                <p>Episodes: ${show.episodes || 'N/A'}</p>
                <div class="seasons-list" id="seasons-list"></div>
            </div>
        `;
        
        // Back button
        document.getElementById('back-btn').onclick = () => {
            this.showView('tv');
        };
        
        // Load seasons
        try {
            const seasons = await API.getSeasons(show.id);
            this.renderSeasons(seasons, show.id);
        } catch (error) {
            console.error('Failed to load seasons:', error);
        }
        
        Navigation.refresh();
    },
    
    // Render seasons
    renderSeasons(seasons, showId) {
        const list = document.getElementById('seasons-list');
        list.innerHTML = '';
        
        seasons.forEach(season => {
            const item = document.createElement('div');
            item.className = 'season-item';
            item.tabIndex = 0;
            item.innerHTML = `<h4>${season.title}</h4>`;
            
            item.onclick = () => this.showSeasonEpisodes(showId, season.season || season.title);
            
            list.appendChild(item);
        });
        
        Navigation.updateFocusableElements();
    },
    
    // Show season episodes
    async showSeasonEpisodes(showId, season) {
        const detailContent = document.getElementById('show-detail-content');
        const info = detailContent.querySelector('.show-detail-info');
        
        // Create episodes container
        let episodesContainer = document.getElementById('episodes-container');
        if (!episodesContainer) {
            episodesContainer = document.createElement('div');
            episodesContainer.id = 'episodes-container';
            episodesContainer.className = 'episodes-grid';
            info.appendChild(episodesContainer);
        }
        
        episodesContainer.innerHTML = '<p>Loading episodes...</p>';
        
        try {
            const episodes = await API.getEpisodes(showId, season);
            this.renderEpisodes(episodes, episodesContainer);
        } catch (error) {
            console.error('Failed to load episodes:', error);
            episodesContainer.innerHTML = '<p>Failed to load episodes</p>';
        }
        
        Navigation.refresh();
    },
    
    // Render episodes
    renderEpisodes(episodes, container) {
        container.innerHTML = '';
        
        episodes.forEach(episode => {
            const card = document.createElement('div');
            card.className = 'episode-card';
            card.tabIndex = 0;
            
            const still = episode.still || '/static/img/placeholder.png';
            const episodeNum = episode.episode ? `Episode ${episode.episode}` : '';
            
            card.innerHTML = `
                <img src="${still}" alt="${episode.title}" loading="lazy">
                <div class="episode-info">
                    <div class="episode-title">${episode.title}</div>
                    <div class="episode-number">${episodeNum}</div>
                </div>
            `;
            
            card.onclick = () => {
                if (episode.id) {
                    // Use episode ID (item_id) for HLS streaming
                    this.playVideo(episode.id);
                }
            };
            
            container.appendChild(card);
        });
        
        Navigation.updateFocusableElements();
    },
    
    // Play video
    playVideo(itemOrFileId) {
        const streamUrl = API.getStreamUrl(itemOrFileId);
        const videoPlayer = document.getElementById('video-player');
        
        // Clean up any existing HLS instance
        if (videoPlayer._hls) {
            videoPlayer._hls.destroy();
            videoPlayer._hls = null;
        }
        
        // Use HLS.js if available, otherwise native player
        if (typeof Hls !== 'undefined' && Hls.isSupported()) {
            const hls = new Hls({
                enableWorker: true,
                lowLatencyMode: false,
                backBufferLength: 90,
                xhrSetup: (xhr, url) => {
                    // Add authentication header for HLS requests
                    const headers = API.getAuthHeaders();
                    Object.keys(headers).forEach(key => {
                        xhr.setRequestHeader(key, headers[key]);
                    });
                }
            });
            hls.loadSource(streamUrl);
            hls.attachMedia(videoPlayer);
            videoPlayer._hls = hls;
            
            // Handle errors
            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    console.error('HLS error:', data);
                    if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                        hls.startLoad();
                    } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                        hls.recoverMediaError();
                    }
                }
            });
        } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
            // Native HLS support (Safari, some Samsung TVs)
            videoPlayer.src = streamUrl;
        } else {
            alert('HLS playback not supported on this device');
            return;
        }
        
        this.showScreen('video');
        
        // Close button
        document.getElementById('video-close-btn').onclick = () => {
            this.closeVideo();
        };
        
        // Auto-play
        videoPlayer.play().catch(err => {
            console.error('Auto-play failed:', err);
        });
    },
    
    // Close video
    closeVideo() {
        const videoPlayer = document.getElementById('video-player');
        videoPlayer.pause();
        
        // Clean up HLS instance
        if (videoPlayer._hls) {
            videoPlayer._hls.destroy();
            videoPlayer._hls = null;
        }
        
        videoPlayer.src = '';
        this.showScreen('main');
        Navigation.refresh();
    },
    
    // Setup navigation
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.showView(view);
            });
        });
    },
    
    // Show view
    showView(viewName) {
        Navigation.currentView = viewName;
        
        // Update nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewName);
        });
        
        // Show/hide views
        document.querySelectorAll('.view').forEach(v => {
            v.classList.toggle('active', v.id === `${viewName}-view`);
        });
        
        // Load content if needed
        if (viewName === 'tv') {
            this.loadTVShows();
        } else if (viewName === 'movies') {
            // Load movies if implemented
        }
        
        Navigation.refresh();
    },
    
    // Setup settings
    setupSettings() {
        // Show current server URL
        document.getElementById('current-server-url').textContent = Config.getServerUrl();
        
        // Change server button
        document.getElementById('change-server-btn').onclick = () => {
            Config.clear();
            this.showScreen('server-config');
        };
        
        // Logout button
        document.getElementById('logout-btn').onclick = () => {
            Config.clear();
            this.showScreen('server-config');
        };
    },
    
    // Show loading message
    showLoadingMessage(message) {
        const msg = document.getElementById('loading-message');
        if (msg) msg.textContent = message;
    },
    
    // Hide loading message
    hideLoadingMessage() {
        // Loading screen is already hidden
    }
};

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    App.init();
}

// Setup server config handlers
document.addEventListener('DOMContentLoaded', () => {
    App.setupServerConfig();
});

