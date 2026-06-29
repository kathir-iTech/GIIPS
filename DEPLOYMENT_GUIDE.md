# DEPLOYMENT_GUIDE.md

## Production Deployment Guide

### 1. Backend (FastAPI)
1.  **Server**: Use `gunicorn` with `uvicorn` workers for production.
    ```bash
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
    ```
2.  **Environment**: Use `.env` files for production configuration (DATABASE_URL, LOG_LEVEL).
3.  **Database**: Migrate from SQLite to PostgreSQL for high-concurrency production environments.

### 2. Frontend (React)
1.  **Build**: Run `npm run build` to generate static assets in `dist/`.
2.  **Hosting**: Serve `dist/` using Nginx or an S3/Cloudfront static hosting setup.
3.  **Config**: Ensure the `BASE_URL` in `src/services/api.ts` points to the production backend API gateway.
