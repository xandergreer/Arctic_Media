# Arctic Media Windows Service Installer
# Requires NSSM (Non-Sucking Service Manager) to be installed

param(
    [string]$InstallPath = "C:\ArcticMedia",
    [string]$ServiceName = "ArcticMedia",
    [string]$User = "LocalSystem"
)

Write-Host "Installing Arctic Media as Windows Service..." -ForegroundColor Green

# Check if NSSM is available
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmPath) {
    Write-Host "NSSM not found. Please install NSSM first:" -ForegroundColor Red
    Write-Host "1. Download from: https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "2. Add nssm.exe to your PATH or place it in the same directory as this script" -ForegroundColor Yellow
    exit 1
}

# Create installation directory
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "Created installation directory: $InstallPath" -ForegroundColor Green
}

# Copy application files (assuming script is run from project root)
$sourcePath = Get-Location
Copy-Item -Path "$sourcePath\app" -Destination "$InstallPath\app" -Recurse -Force
Copy-Item -Path "$sourcePath\run_server.py" -Destination "$InstallPath\" -Force
Copy-Item -Path "$sourcePath\requirements.txt" -Destination "$InstallPath\" -Force
Copy-Item -Path "$sourcePath\arctic.db" -Destination "$InstallPath\" -Force -ErrorAction SilentlyContinue

# Create data and transcode directories
New-Item -ItemType Directory -Path "$InstallPath\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallPath\transcode" -Force | Out-Null

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Host "Python not found in PATH. Please install Python 3.11+ and try again." -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path "$InstallPath\.venv")) {
    python -m venv "$InstallPath\.venv"
}

# Install requirements
& "$InstallPath\.venv\Scripts\pip.exe" install -r "$InstallPath\requirements.txt"

# Install service using NSSM
Write-Host "Installing service using NSSM..." -ForegroundColor Yellow

# Remove existing service if it exists
& nssm stop $ServiceName 2>$null
& nssm remove $ServiceName confirm 2>$null

# Install new service
& nssm install $ServiceName "$InstallPath\.venv\Scripts\python.exe" "app.main:app"
& nssm set $ServiceName AppDirectory "$InstallPath"
& nssm set $ServiceName AppParameters "-m uvicorn --host 0.0.0.0 --port 8000"
& nssm set $ServiceName DisplayName "Arctic Media Server"
& nssm set $ServiceName Description "Self-hosted media streaming server"
& nssm set $ServiceName Start SERVICE_AUTO_START

# Set environment variables
& nssm set $ServiceName AppEnvironmentExtra "ARCTIC_MEDIA_ROOT=$InstallPath\data" "ARCTIC_TRANSCODE_DIR=$InstallPath\transcode" "FFMPEG_BIN=ffmpeg" "FFMPEG_PRESET=veryfast" "HLS_SEG_DUR=2.0"

# Set user account
& nssm set $ServiceName ObjectName $User

# Start the service
Write-Host "Starting Arctic Media service..." -ForegroundColor Yellow
& nssm start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "Arctic Media service installed and started successfully!" -ForegroundColor Green
    Write-Host "Service name: $ServiceName" -ForegroundColor Cyan
    Write-Host "Access URL: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Media directory: $InstallPath\data" -ForegroundColor Cyan
    Write-Host "" -ForegroundColor White
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  Start service: nssm start $ServiceName" -ForegroundColor White
    Write-Host "  Stop service:  nssm stop $ServiceName" -ForegroundColor White
    Write-Host "  Remove service: nssm remove $ServiceName confirm" -ForegroundColor White
}
else {
    Write-Host "Failed to start service. Check the service configuration." -ForegroundColor Red
    exit 1
}
