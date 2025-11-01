@echo off
REM Quick batch wrapper for PowerShell script
REM Usage: build-and-deploy.bat [FireTV_IP]

if "%1"=="" (
    powershell.exe -ExecutionPolicy Bypass -File "%~dp0build-and-deploy.ps1" -BuildOnly
) else (
    powershell.exe -ExecutionPolicy Bypass -File "%~dp0build-and-deploy.ps1" -FireTVIP "%1"
)

