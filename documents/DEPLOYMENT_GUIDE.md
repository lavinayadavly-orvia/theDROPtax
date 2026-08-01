# Deployment Guide

This guide provides step-by-step instructions for deploying the DROP Tax application to production.

## Infrastructure Overview

| Component | Service Provider | Link/Console |
| :--- | :--- | :--- |
| **Frontend** | Cloudflare Pages | [droptaxai](https://dash.cloudflare.com) |
| **Backend** | Render (Web Service) | see `BACKEND_URL` env var in Cloudflare Pages |
| **Database** | MongoDB Atlas | [Cluster0](https://cloud.mongodb.com) |

## Environment Variables

### Backend (.env)
Required on Render:
- `MONGO_URL`: MongoDB connection string.
- `DB_NAME`: Database name (e.g., `droptax`).
- `TAVILY_API_KEY`: For real-time web search.
- `OPENAI_API_KEY`: For AI synthesis and strategic briefing.
- `FRONTEND_URL`: URL of the deployed frontend (for CORS).

### Frontend (.env)
Required for local builds/Cloudflare:
- `REACT_APP_BACKEND_URL`: URL of the Render backend (optional, as proxy handles this in production).

## Deployment Steps

### 1. Backend (Render)
The backend is configured to auto-deploy from the `main` branch.
1. Push changes to the GitHub repository.
2. Render will automatically trigger a build using the `Dockerfile` in the `backend/` directory.

### 2. Frontend (Cloudflare Pages)
The frontend uses a custom deployment script to handle the reverse proxy (`_worker.js`).

**Manual Deployment via CLI:**
1. Navigate to the frontend directory: `cd frontend`
2. Build the project: `npm run build`
3. Prepare the `dist` folder:
   ```bash
   cp dist/_worker.js /tmp/_worker_backup.js
   rm -rf dist
   cp -r build dist
   cp /tmp/_worker_backup.js dist/_worker.js
   ```
4. Deploy to Cloudflare:
   ```bash
   npx wrangler pages deploy dist --project-name droptaxai
   ```

## API Routing & Reverse Proxy
The application uses a Cloudflare Worker (`frontend/dist/_worker.js`) to route API requests. 
- Requests to `/api/*` are forwarded to the host set in the `BACKEND_URL` environment variable (Cloudflare Pages → Settings → Environment variables).
- All other requests serve the React static files.

> [!IMPORTANT]
> When updating the frontend, ensure `_worker.js` is preserved in the `dist` folder, or API calls will fail in production.
