# PLACEWISE Development Server Launcher
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Starting PLACEWISE (Backend + Frontend) " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Start FastAPI Backend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Start Vite React Frontend
Set-Location "$PSScriptRoot\frontend"
npm run dev

