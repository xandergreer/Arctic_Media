#!/bin/bash

# Arctic Media Server Deployment Script
# This script sets up Arctic Media Server on a Linux system

set -e

# Configuration
INSTALL_DIR="/opt/arctic-media"
SERVICE_USER="arctic"
SERVICE_NAME="arctic-media"
PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 0 ]]; then
        log_error "Python 3.11 or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
    
    # Check ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        log_warning "ffmpeg not found. Please install ffmpeg before continuing."
        log_info "Install ffmpeg with: sudo apt install ffmpeg (Ubuntu/Debian) or sudo yum install ffmpeg (CentOS/RHEL)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "System requirements check passed"
}

# Create user and directories
setup_user_and_dirs() {
    log_info "Setting up user and directories..."
    
    # Create user if it doesn't exist
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --create-home --shell /bin/bash "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_info "User $SERVICE_USER already exists"
    fi
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/data"
    mkdir -p "$INSTALL_DIR/transcode"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    log_success "Directories created and permissions set"
}

# Install application
install_application() {
    log_info "Installing application..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Copy application files
    cp -r "$PROJECT_ROOT/app" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/run_server.py" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/requirements.txt" "$INSTALL_DIR/"
    
    # Copy database if it exists
    if [[ -f "$PROJECT_ROOT/arctic.db" ]]; then
        cp "$PROJECT_ROOT/arctic.db" "$INSTALL_DIR/"
        chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/arctic.db"
    fi
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    log_success "Application files copied"
}

# Setup Python environment
setup_python_env() {
    log_info "Setting up Python environment..."
    
    # Switch to service user for Python setup
    su - "$SERVICE_USER" << EOF
        cd "$INSTALL_DIR"
        
        # Create virtual environment
        python3 -m venv .venv
        
        # Activate and install requirements
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        
        # Create a simple startup script
        cat > start.sh << 'START_SCRIPT'
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
export ARCTIC_MEDIA_ROOT="$INSTALL_DIR/data"
export ARCTIC_TRANSCODE_DIR="$INSTALL_DIR/transcode"
export FFMPEG_BIN=ffmpeg
export FFMPEG_PRESET=veryfast
export HLS_SEG_DUR=2.0
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
START_SCRIPT
        
        chmod +x start.sh
EOF
    
    log_success "Python environment setup complete"
}

# Install systemd service
install_service() {
    log_info "Installing systemd service..."
    
    # Copy service file
    cp "$SCRIPT_DIR/arctic-media.service" /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service installed and enabled"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    # Check if ufw is available (Ubuntu)
    if command -v ufw &> /dev/null; then
        ufw allow "$PORT/tcp"
        log_success "UFW firewall configured"
    # Check if firewalld is available (CentOS/RHEL)
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port="$PORT/tcp"
        firewall-cmd --reload
        log_success "Firewalld configured"
    else
        log_warning "No supported firewall found. Please manually open port $PORT"
    fi
}

# Start service
start_service() {
    log_info "Starting Arctic Media Server..."
    
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for startup
    sleep 3
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Arctic Media Server is running!"
    else
        log_error "Failed to start service. Check logs with: journalctl -u $SERVICE_NAME"
        exit 1
    fi
}

# Display final information
show_final_info() {
    echo
    log_success "Arctic Media Server installation complete!"
    echo
    echo "Service Information:"
    echo "  Service Name: $SERVICE_NAME"
    echo "  Install Directory: $INSTALL_DIR"
    echo "  Media Directory: $INSTALL_DIR/data"
    echo "  Access URL: http://localhost:$PORT"
    echo
    echo "Useful Commands:"
    echo "  Start service:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
    echo "  Status:          sudo systemctl status $SERVICE_NAME"
    echo
    echo "Next Steps:"
    echo "1. Add your media files to: $INSTALL_DIR/data"
    echo "2. Access the web interface at: http://localhost:$PORT"
    echo "3. Create an admin user through the web interface"
    echo
}

# Main installation function
main() {
    echo "Arctic Media Server Deployment Script"
    echo "===================================="
    echo
    
    check_root
    check_requirements
    setup_user_and_dirs
    install_application
    setup_python_env
    install_service
    configure_firewall
    start_service
    show_final_info
}

# Run main function
main "$@"
