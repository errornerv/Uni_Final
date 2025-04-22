@echo off
setlocal EnableDelayedExpansion

:: Execution counter
set COUNTER=0

:: Log file path (equivalent to /tmp in Windows)
set LOGFILE=C:\Users\%USERNAME%\freedns_Kyra-Tube_evils_in.log

:: Initial execution
:initial
echo Updating FreeDNS...
curl -s "http://sync.afraid.org/u/t7Ge75sBuu24edyhP25mcQfJ/" >> %LOGFILE% 2>nul
set /a COUNTER+=1
echo Update completed! Number of executions: !COUNTER! times

:: Loop to repeat every 5 minutes
:loop
:: 5-minute timer (300 seconds)
for /l %%i in (300,-1,1) do (
    set /a mins=%%i/60
    set /a secs=%%i%%60
    <nul set /p dummy=Time remaining: !mins!:!secs! 
    ping -n 2 127.0.0.1 >nul
    cls
)

:: Update again
echo Updating FreeDNS...
curl -s "http://sync.afraid.org/u/t7Ge75sBuu24edyhP25mcQfJ/" >> %LOGFILE% 2>nul
set /a COUNTER+=1
echo Update completed! Number of executions: !COUNTER! times

goto loop