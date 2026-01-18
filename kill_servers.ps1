taskkill /F /IM ArcticMedia.exe
taskkill /F /IM python.exe
taskkill /F /IM ffprobe.exe
taskkill /F /IM ffmpeg.exe

if ($?) { Write-Host "All processes killed." } else { Write-Host "Some processes were not found (clean)." }
