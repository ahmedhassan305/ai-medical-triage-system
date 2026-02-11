# AI Medical Triage System (Monorepo)

## Structure
- `backend/`: FastAPI API
- `frontend/`: React + Vite web app

## Backend (FastAPI)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:
```powershell
cd backend
.\.venv\Scripts\activate
pytest
```

## Frontend (React + Vite)
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Default URLs:
- API: `http://localhost:8000`
- Web: `http://localhost:5173`

## Git Init
```powershell
git init
git checkout -b main
git checkout -b dev
git checkout main
git add .
git commit -m "Initial monorepo scaffold"
```
