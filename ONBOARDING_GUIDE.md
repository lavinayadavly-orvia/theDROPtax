# DROP Tax Master Onboarding Documentation

This document provides a technical blueprint of the DROP Tax application for the incoming engineering team. It covers environment configuration, dependency mapping, local setup, and deployment architecture.

## 1. Environment & Secrets Inventory

### Configuration Matrix

| Variable | Category | Status | Description |
| :--- | :--- | :--- | :--- |
| `MONGO_URL` | Database | **Required** | MongoDB Atlas connection string (with credentials). |
| `DB_NAME` | Database | **Required** | Target database name (default: `droptax`). |
| `TAVILY_API_KEY`| External API | Optional | Required for real-time web-sweeper/intelligence audits. |
| `OPENAI_API_KEY`| External API | Optional | Required for AI Strategic Briefing synthesis (GPT-4). |
| `FRONTEND_URL`  | Auth/CORS | Optional | Allowed origin for CORS (default: `http://localhost:3000`). |
| `REACT_APP_BACKEND_URL` | Frontend | Optional | API base URL for frontend (default: `http://localhost:8000`). |

> [!WARNING]
> **Security Alert: Hardcoded Secrets Discovery**
> - `backend/seed_regions.py`: Contains a hardcoded MongoDB Atlas URI with plaintext credentials. 
> - `backend/server.py`: Contains fallback logic with hardcoded API keys for testing.
> - **Action Required**: Extract these into a secure secret manager or `.env` file immediately.

---

## 2. Dependency & Third-Party Integration Map

### Core Infrastructure
- **Backend Stack**: Python 3.11, FastAPI (Asynchronous Framework), Uvicorn (ASGI Server).
- **Database**: MongoDB Atlas (v7.0+ recommended), accessed via `motor` (async driver).
- **Frontend Stack**: React 19 (SPA), Tailwind CSS, Craco (Webpack override).
- **PDF Engine**: ReportLab (Serverside generation for Global Value Dossiers).

### Third-Party Services
- **Tavily AI**: Used for high-speed, LLM-optimized web searching for clinical threats.
- **OpenAI (GPT-4)**: Powers the "Strategic Brief" synthesis engine.
- **Cloudflare Pages**: Hosts the static frontend assets.
- **Render.com**: Hosts the live Python backend service.

### Critical Libraries
- `driver.js`: Interactive onboarding tour engine.
- `recharts`: D3-based visualization for cost and liability charts.
- `radix-ui`: Underlying headless components for accessibility.

---

## 3. Step-by-Step Local Development Setup Guide

### Prerequisites
- **Node.js**: v18.0 or higher
- **Python**: v3.11 or higher
- **MongoDB**: Local instance or access to the provided Atlas cluster

### Backend Setup
1. **Navigate and Initialize**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Create a `.env` file in `backend/` using the values found in Section 1.
4. **Bootstrap Database**:
   ```bash
   python seed_regions.py
   ```
5. **Run Server**:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup
1. **Navigate and Install**:
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   ```
2. **Run Dev Server**:
   ```bash
   npm start
   ```
   *Note: The frontend is configured to proxy `/api` requests to `localhost:8000` via `package.json` proxy settings.*

---

## 4. Server Deployment & Build Blueprint

### Build Process
- **Frontend Build**: `CI=false npm run build`. The `CI=false` flag is required to bypass strict ESLint warnings that otherwise fail the build.
- **Backend Build**: Standard Python environment setup via `pip`.

### Deployment Architecture
The application uses a **Split-Origin Proxy Architecture**:
1. **Edge (Cloudflare Pages)**: Serves the static React build.
2. **Proxy Layer (`public/_worker.js`)**: A Cloudflare Fetch Worker that intercepts all `/api/*` calls and redirects them to the Render backend.
3. **Origin (Render.com)**: Securely hosts the FastAPI engine.

#### Containerization (Dockerfile)
A `backend/Dockerfile` exists using `python:3.11-slim`. It is a single-stage build that installs system dependencies (`libffi`, `libssl`), pip installs requirements, and runs uvicorn.

---

## 5. Onboarding Roadblocks (SRE Warning List)

1. **Proxy URL Hardcoding**: The Cloudflare worker (`_worker.js`) has a **hardcoded production URL** for the backend. Changing deployments requires manually updating this file.
2. **Environment Synchronization**: There is no `.env.example`. New developers must hunt through `server.py` to identify required keys.
3. **CORS Configuration**: The backend CORS middleware defaults to allowed origins; however, strict production environments may reject the Cloudflare worker proxy if headers aren't perfectly aligned.
4. **Seed vs. Migrations**: The system relies on `seed_regions.py` for schema initialization. There is no versioned migration system (like Alembic).
5. **PDF Font Issues**: ReportLab occasionally requires specific system fonts for non-Latin characters (INR/AED symbols) which may fail inside the slim Docker container if not handled.
