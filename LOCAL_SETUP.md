# CampusAI Hackathon Local Setup Guide

This guide explains how to run the full app on a fresh local machine.

## What You Are Running

- Frontend: React + Vite in `stuff`
- Backend: FastAPI in `stuff/backend`
- Default ports:
  - Frontend: `5173`
  - Backend: `8005`

## Prerequisites

- Git installed
- Node.js 18+ and npm
- Python 3.10+
- Internet access (for package installs and OpenAI API calls)

## 2) Set Up Python Environment (Backend)

### macOS / Linux

```bash
python3 -m venv env
source env/bin/activate
pip install -r stuff/backend/requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r stuff/backend/requirements.txt
```

## 3) Set OpenAI API Key

You need a valid key for LLM-based major and keyword extraction.

### macOS / Linux (current terminal)

```bash
export OPENAI_API_KEY="your_openai_key_here"
```

### Windows (PowerShell, current terminal)

```powershell
$env:OPENAI_API_KEY="your_openai_key_here"
```

Optional persistent setup:

- macOS/Linux: add the export line to `~/.zshrc` or `~/.bashrc`
- Windows: set a user environment variable in System Settings

## 4) Start Backend

From the repo root:

### macOS / Linux

```bash
source env/bin/activate
cd stuff/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### Windows (PowerShell)

```powershell
.\env\Scripts\Activate.ps1
cd stuff\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

Backend should be available at:

- `http://localhost:8005`

Useful backend endpoints:

- `GET /goals`
- `POST /goals`
- `GET /plan`
- `GET /electives`
- `GET /downstream-object`

## 5) Start Frontend

Open a second terminal, from repo root:

```bash
cd stuff
npm install
npm run dev
```

Frontend should be available at:

- `http://localhost:5173`

## 6) Optional Frontend API Override

Frontend uses:

- `VITE_API_URL` if set
- otherwise defaults to `http://localhost:8005`

Create `stuff/.env` if you want a custom backend URL:

```env
VITE_API_URL=http://localhost:8005
```

## 7) Quick Health Check

From repo root:

```bash
curl -s -X POST "http://localhost:8005/goals" \
  -H "Content-Type: application/json" \
  -d '{"text":"I want to work in AI product strategy"}'
```

Expected result:

- JSON response with `suggested_major`
- `keywords`
- `electives`
- `downstream_object` (contains concatenated major + keywords)

## Troubleshooting

### Port already in use

If `8005` or `5173` is occupied, stop conflicting processes or run on a different port.

### OpenAI not being used

- Verify key is set in the same terminal session as the backend process.
- Test key quickly:

```bash
echo "$OPENAI_API_KEY"
```

If missing, set it and restart backend.

### Python package import errors

Make sure virtual environment is activated before running backend.

### Frontend cannot reach backend

- Confirm backend is running on `8005`
- Confirm frontend API base URL is correct (`VITE_API_URL` or default)

## Security Notes

- Never commit real API keys to git.
- Rotate any key that was exposed in chat, terminal output, or source files.
