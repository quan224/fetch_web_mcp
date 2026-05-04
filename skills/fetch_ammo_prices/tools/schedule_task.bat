@echo off

set TASK_NAME=CollectAmmoPrices
set VBS_PATH=%~dp0collect_ammo_prices_silent.vbs

if "%~1"=="" goto :usage
if /i "%~1"=="install" goto :install
if /i "%~1"=="uninstall" goto :uninstall
if /i "%~1"=="status" goto :status
goto :usage

:install
echo Creating scheduled task [%TASK_NAME%] ...
schtasks //create //tn "%TASK_NAME%" //tr "wscript.exe \"%VBS_PATH%\"" //sc hourly //mo 1 //st 00:00 //f
if %errorlevel%==0 (
    echo [OK] Task created. Runs every hour.
    echo      Use "%~nx0 uninstall" to remove.
) else (
    echo [FAIL] Try running as Administrator.
)
goto :end

:uninstall
echo Deleting scheduled task [%TASK_NAME%] ...
schtasks //delete //tn "%TASK_NAME%" //f
if %errorlevel%==0 (
    echo [OK] Task deleted.
) else (
    echo [FAIL] Task may not exist or needs admin rights.
)
goto :end

:status
schtasks //query //tn "%TASK_NAME%" //v //fo LIST 2>nul
if %errorlevel% neq 0 (
    echo [STATUS] Task not created.
    echo          Use "%~nx0 install" to create.
)
goto :end

:usage
echo Usage: %~nx0 [install^|uninstall^|status]
echo.
echo   install   - Create hourly scheduled task
echo   uninstall - Remove scheduled task
echo   status    - Show task status
echo.
echo Note: May require Administrator privileges.

:end
