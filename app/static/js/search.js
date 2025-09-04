// Search functionality for Arctic Media
class Search {
    constructor() {
        this.searchContainer = document.querySelector('.search-container');
        this.searchBtn = document.getElementById('search-btn');
        this.searchInputWrapper = document.querySelector('.search-input-wrapper');
        this.searchInput = document.getElementById('search-input');
        this.searchClear = document.getElementById('search-clear');
        this.searchResultsPopup = document.getElementById('search-results');

        this.searchTimeout = null;
        this.isExpanded = false;

        this.init();
    }

    init() {
        this.searchBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleSearch();
        });

        this.searchClear?.addEventListener('click', () => this.clearSearch());
        this.searchInput?.addEventListener('input', (e) => this.handleSearch(e.target.value));
        this.searchInput?.addEventListener('keydown', (e) => this.handleKeydown(e));

        // Collapse search when clicking outside
        document.addEventListener('click', (e) => this.handleOutsideClick(e));

        // Collapse on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isExpanded) {
                e.preventDefault();
                this.collapseSearch();
            }
        });

        // Expand on Ctrl+K or Cmd+K
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.expandSearch();
            }
        });
    }

    toggleSearch() {
        if (this.isExpanded) {
            this.collapseSearch();
        } else {
            this.expandSearch();
        }
    }

    expandSearch() {
        if (this.isExpanded) return;
        this.isExpanded = true;
        this.searchBtn.style.display = 'none';
        this.searchInputWrapper.classList.add('expanded');

        // Focus after animation
        setTimeout(() => {
            this.searchInput.focus();
            this.updateClearButton();
        }, 300);
    }

    collapseSearch() {
        if (!this.isExpanded) return;
        this.isExpanded = false;
        this.searchInput.value = '';
        this.updateClearButton();
        this.clearSearchTimeout();
        this.searchResultsPopup.classList.remove('visible');
        this.searchInputWrapper.classList.remove('expanded');

        // Show button after animation
        setTimeout(() => {
            this.searchBtn.style.display = 'flex';
        }, 300);
    }

    handleOutsideClick(e) {
        if (this.isExpanded && !this.searchContainer.contains(e.target)) {
            this.collapseSearch();
        }
    }

    clearSearch() {
        this.searchInput.value = '';
        this.searchInput.focus();
        this.updateClearButton();
        this.showPlaceholder();
        this.clearSearchTimeout();
    }

    updateClearButton() {
        if (this.searchClear) {
            this.searchClear.style.display = this.searchInput.value ? 'flex' : 'none';
        }
    }

    handleKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const firstResult = this.searchResultsPopup.querySelector('.search-result-item');
            if (firstResult) {
                firstResult.click();
            }
        }
    }

    handleSearch(query) {
        this.updateClearButton();
        this.clearSearchTimeout();

        if (!query || query.length < 2) {
            this.showPlaceholder();
            return;
        }

        // Show results popup
        this.searchResultsPopup.classList.add('visible');

        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }

    clearSearchTimeout() {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = null;
        }
    }

    async performSearch(query) {
        this.showLoading();

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.renderResults(data.movies, data.tv_shows);
        } catch (error) {
            console.error('Search failed:', error);
            this.showError();
        }
    }

    renderResults(movies, tvShows) {
        this.searchResultsPopup.innerHTML = '';

        if (movies.length === 0 && tvShows.length === 0) {
            this.showNoResults();
            return;
        }

        if (movies.length > 0) {
            this.searchResultsPopup.innerHTML += this.renderSection('Movies', movies, 'movie');
        }
        if (tvShows.length > 0) {
            this.searchResultsPopup.innerHTML += this.renderSection('TV Shows', tvShows, 'tv');
        }
    }

    renderSection(title, items, type) {
        let html = `<div class="search-section"><h3 class="search-section-title">${title}</h3>`;
        items.forEach(item => {
            const posterUrl = item.poster_url || '/static/img/placeholder.png';
            const itemYear = item.year ? `(${item.year})` : '';
            const itemOverview = item.overview || 'No overview available.';
            html += `
                <a href="/${type === 'movie' ? 'movie' : 'show'}/${item.id}" class="search-result-item">
                    <img src="${posterUrl}" alt="${item.title}" class="search-result-poster">
                    <div class="search-result-info">
                        <h4 class="search-result-title">${item.title}</h4>
                        <p class="search-result-year">${itemYear}</p>
                        <span class="search-result-type">${type === 'movie' ? 'Movie' : 'TV Show'}</span>
                        <p class="search-result-overview">${itemOverview}</p>
                    </div>
                </a>
            `;
        });
        html += `</div>`;
        return html;
    }

    showLoading() {
        this.searchResultsPopup.innerHTML = `
            <div class="search-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
                    <path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z">
                        <animateTransform attributeName="transform" type="rotate" dur="1s" repeatCount="indefinite" from="0 12 12" to="360 12 12"/>
                    </path>
                </svg>
                <p>Searching...</p>
            </div>
        `;
        this.searchResultsPopup.classList.add('visible');
    }

    showPlaceholder() {
        this.searchResultsPopup.innerHTML = `
            <div class="search-placeholder">
                <p>Start typing to search movies and TV shows</p>
            </div>
        `;
        this.searchResultsPopup.classList.add('visible');
    }

    showNoResults() {
        this.searchResultsPopup.innerHTML = `
            <div class="search-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                <p>No results found.</p>
            </div>
        `;
        this.searchResultsPopup.classList.add('visible');
    }

    showError() {
        this.searchResultsPopup.innerHTML = `
            <div class="search-placeholder">
                <p>An error occurred during search. Please try again.</p>
            </div>
        `;
        this.searchResultsPopup.classList.add('visible');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Search();
});
