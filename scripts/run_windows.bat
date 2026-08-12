@echo off

rem Navigate to the project root (one level up from scripts/)
set "DIR=%~dp0.."
cd /d "%DIR%"

echo ========================================================
echo    AkshayKala AI Studio (Gradio UI)
echo ========================================================

echo.
echo Building unified Docker environment (this is fast after the first run)...
docker build -t akshaykala-ai-studio "%DIR%" --quiet

echo.
echo ========================================================
echo Launching Master Pipeline Web Interface...
echo.
echo PLEASE WAIT... The AI models are loading.
echo Do NOT open the browser until you see this message below:
echo    'Running on local URL:  http://0.0.0.0:7860'
echo.
echo Once you see that, open your browser and go to:
echo    http://localhost:7860
echo ========================================================
echo Press Ctrl+C in this terminal to stop the server.
echo.

docker run -it --rm ^
  -p 7860:7860 ^
  -v "%DIR%:/app" ^
  -w "/app" ^
  akshaykala-ai-studio

pause
