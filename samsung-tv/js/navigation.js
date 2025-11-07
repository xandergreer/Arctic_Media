// Navigation and Remote Control Handling
const Navigation = {
    currentFocus: null,
    focusableElements: [],
    currentView: 'home',
    
    // Initialize navigation
    init() {
        // Handle key events
        document.addEventListener('keydown', (e) => this.handleKey(e));
        
        // Track focusable elements
        this.updateFocusableElements();
        
        // Set initial focus
        this.setInitialFocus();
    },
    
    // Update list of focusable elements
    updateFocusableElements() {
        const view = document.querySelector('.view.active');
        if (!view) return;
        
        this.focusableElements = Array.from(view.querySelectorAll(
            '.nav-item, .content-card, .btn, input, .season-item, .episode-card'
        )).filter(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden';
        });
        
        // Add nav items if main screen is active
        if (document.getElementById('main-screen').classList.contains('active')) {
            const navItems = Array.from(document.querySelectorAll('.nav-item'));
            this.focusableElements = [...navItems, ...this.focusableElements];
        }
    },
    
    // Handle keyboard input
    handleKey(e) {
        const key = e.key;
        
        // Prevent default behavior for TV remote keys
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter', 'Backspace'].includes(key)) {
            e.preventDefault();
        }
        
        switch(key) {
            case 'ArrowRight':
                this.moveFocus('next');
                break;
            case 'ArrowLeft':
                this.moveFocus('prev');
                break;
            case 'ArrowDown':
                this.moveFocus('down');
                break;
            case 'ArrowUp':
                this.moveFocus('up');
                break;
            case 'Enter':
                this.activateFocused();
                break;
            case 'Backspace':
            case 'Escape':
                this.handleBack();
                break;
        }
    },
    
    // Move focus
    moveFocus(direction) {
        if (this.focusableElements.length === 0) {
            this.updateFocusableElements();
        }
        
        if (this.focusableElements.length === 0) return;
        
        const currentIndex = this.currentFocus 
            ? this.focusableElements.indexOf(this.currentFocus)
            : -1;
        
        let nextIndex = currentIndex;
        
        // Handle grid navigation (for content cards)
        if (direction === 'next' || direction === 'right') {
            nextIndex = currentIndex + 1;
        } else if (direction === 'prev' || direction === 'left') {
            nextIndex = currentIndex - 1;
        } else if (direction === 'down') {
            // For grid layouts, move down by calculating columns
            const grid = this.getGridLayout();
            if (grid.cols > 0) {
                nextIndex = currentIndex + grid.cols;
            } else {
                nextIndex = currentIndex + 1;
            }
        } else if (direction === 'up') {
            const grid = this.getGridLayout();
            if (grid.cols > 0) {
                nextIndex = currentIndex - grid.cols;
            } else {
                nextIndex = currentIndex - 1;
            }
        }
        
        // Wrap around
        if (nextIndex < 0) {
            nextIndex = this.focusableElements.length - 1;
        } else if (nextIndex >= this.focusableElements.length) {
            nextIndex = 0;
        }
        
        this.setFocus(this.focusableElements[nextIndex]);
    },
    
    // Get grid layout info
    getGridLayout() {
        const grid = document.querySelector('.content-grid.active, .content-grid');
        if (!grid) return { cols: 0 };
        
        const style = window.getComputedStyle(grid);
        const template = style.gridTemplateColumns;
        const cols = template.split(' ').length;
        
        return { cols };
    },
    
    // Set focus on element
    setFocus(element) {
        if (!element) return;
        
        // Remove previous focus
        if (this.currentFocus) {
            this.currentFocus.classList.remove('focused');
        }
        
        // Set new focus
        this.currentFocus = element;
        element.classList.add('focused');
        element.focus();
        
        // Update focus indicator
        this.updateFocusIndicator(element);
        
        // Scroll into view
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },
    
    // Update focus indicator
    updateFocusIndicator(element) {
        const indicator = document.getElementById('focus-indicator');
        if (!indicator) return;
        
        const rect = element.getBoundingClientRect();
        indicator.style.left = `${rect.left - 4}px`;
        indicator.style.top = `${rect.top - 4}px`;
        indicator.style.width = `${rect.width + 8}px`;
        indicator.style.height = `${rect.height + 8}px`;
        indicator.classList.add('visible');
    },
    
    // Set initial focus
    setInitialFocus() {
        this.updateFocusableElements();
        if (this.focusableElements.length > 0) {
            this.setFocus(this.focusableElements[0]);
        }
    },
    
    // Activate focused element
    activateFocused() {
        if (!this.currentFocus) return;
        
        // Trigger click
        if (this.currentFocus.onclick) {
            this.currentFocus.onclick();
        } else {
            this.currentFocus.click();
        }
    },
    
    // Handle back button
    handleBack() {
        // If in video player, close it
        if (document.getElementById('video-screen').classList.contains('active')) {
            App.closeVideo();
            return;
        }
        
        // If in detail view, go back
        if (document.getElementById('show-detail-view').classList.contains('active')) {
            App.showView('tv');
            return;
        }
        
        // If in settings, go to home
        if (this.currentView === 'settings') {
            App.showView('home');
            return;
        }
    },
    
    // Refresh navigation after view change
    refresh() {
        this.updateFocusableElements();
        this.setInitialFocus();
    }
};

