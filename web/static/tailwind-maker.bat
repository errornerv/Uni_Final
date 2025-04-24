@echo off
cd /d "C:\Programming\Git-Hub\Uni_Final\web\static"
echo Current directory: %CD%
echo Checking for input.css...
if not exist "input.css" (
    echo Error: input.css not found in %CD%
    pause
    exit /b 1
)
echo input.css found.
echo Checking if tailwindcss is installed...
npx tailwindcss --version
if %ERRORLEVEL% NEQ 0 (
    echo Error: tailwindcss is not installed. Run 'npm install -D tailwindcss' first.
    pause
    exit /b 1
)
echo tailwindcss is installed.
echo Running Tailwind CSS compiler...
npx tailwindcss -i ./input.css -o ./styles.css --watch
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to run Tailwind CSS compiler. Check the error above.
    pause
    exit /b 1
)
pause