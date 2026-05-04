@echo off
chcp 65001 >nul

REM ========== Auto-detect Git Bash ==========
set "GIT_BASH="
REM Method 1: derive from `where git`
for /f "delims=" %%i in ('where git 2^>nul') do (
    for %%j in ("%%i\..\..\bin\bash.exe") do (
        if exist "%%~fj" set "GIT_BASH=%%~fj"
    )
)
REM Method 2: common install paths
if not defined GIT_BASH (
    for %%p in (
        "%ProgramFiles%\Git\bin\bash.exe"
        "%ProgramFiles(x86)%\Git\bin\bash.exe"
        "C:\Program Files\Git\bin\bash.exe"
        "D:\Git\bin\bash.exe"
    ) do (
        if exist %%p set "GIT_BASH=%%~p"
    )
)
if defined GIT_BASH set "CLAUDE_CODE_GIT_BASH_PATH=%GIT_BASH%"

REM ========== Auto-detect claude CLI ==========
REM Add common npm paths
set "PATH=%PATH%;%APPDATA%\npm"

REM ========== Run collection ==========
cd /d "%~dp0.."

echo ============================================
echo  Ammo Price Collection
echo  Time: %date% %time%
echo ============================================
echo.

claude -p "Follow the SKILL.md in current directory to collect ammo prices. Requirements: 1) Auto-detect browser path (prefer Edge); 2) Check login status; 3) Extract data by grade (5-1) using URL grade parameter; 4) Save to data\ as ammo_prices_YYYYMMDD_HHmm.json; 5) Run tools\merge_history.py; 6) Update website; 7) Shutdown browser; 8) All tool calls use isHeadless=true." --allowedTools "mcp__fetch-webpage__*" "Bash" "Read" "Write" "Edit" "Glob" "Grep" --add-dir "%~dp0.."

echo.
echo ============================================
echo  Done: %date% %time%
echo ============================================

echo [%date% %time%] Collection complete >> "%~dp0..\data\collect_log.txt"
