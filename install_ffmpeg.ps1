$ErrorActionPreference = "Stop"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zipPath = "e:\Arctic_Media\ffmpeg.zip"
$destDir = "e:\Arctic_Media\ffmpeg_temp"
$finalDir = "e:\Arctic_Media\ffmpeg"

Write-Host "Downloading FFmpeg from $url..."
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $destDir -Force

Write-Host "Organizing files..."
# Find the bin folder wherever it extracted
$binPath = Get-ChildItem -Path $destDir -Recurse -Filter "bin" | Select-Object -First 1
if ($binPath) {
    New-Item -ItemType Directory -Force -Path $finalDir | Out-Null
    Copy-Item -Path "$($binPath.FullName)\*" -Destination $finalDir -Force
    Write-Host "FFmpeg installed to $finalDir"
    
    # Test it
    & "$finalDir\ffmpeg.exe" -version | Select-Object -First 1
}
else {
    Write-Host "Error: Could not find bin folder in extracted zip"
    exit 1
}

# Cleanup
Remove-Item -Path $zipPath -Force
Remove-Item -Path $destDir -Recurse -Force
Write-Host "Done."
