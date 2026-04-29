Set-Location "$PSScriptRoot\.."
docker compose up -d postgres ollama
docker compose ps postgres ollama
