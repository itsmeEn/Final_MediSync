## Deployment: Render (Backend) + Cloudflare Pages (Frontend)

### Backend (Render)

#### Render Service Type
- Create a **Web Service** from this repo.
- Runtime: **Python**

#### Build Command
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput || true
```

#### Start Command (ASGI)
```bash
daphne -b 0.0.0.0 -p $PORT backend.asgi:application
```

#### Required Environment Variables (Render)
- `DJANGO_SECRET_KEY`: strong secret
- `DJANGO_DEBUG`: `false`
- `ALLOWED_HOSTS`: include your Render hostname (optional if Render sets `RENDER_EXTERNAL_HOSTNAME`)
- `CORS_ALLOWED_ORIGINS`: your Cloudflare Pages domain(s), comma-separated
  - Example: `https://medisync.pages.dev,https://app.example.com`
- `CSRF_TRUSTED_ORIGINS`: your Cloudflare Pages domain(s), comma-separated (recommended)
  - Example: `https://medisync.pages.dev,https://app.example.com`
- `FRONTEND_URL`: your Cloudflare Pages URL
- Database:
  - Prefer Render Postgres `DATABASE_URL` (Render provides this when you attach a Postgres instance)
- Redis (required for Channels/WebSockets + cache; recommended for Celery):
  - `REDIS_URL`: e.g. `redis://:<password>@<host>:6379/0`
- Email (optional):
  - `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- Encryption:
  - `MESSAGE_ENCRYPTION_KEY`

### Frontend (Cloudflare Pages)

#### Build Settings
- Framework preset: **None** (or “Vite” if you prefer; Quasar uses Vite under the hood)
- Build command:
```bash
npm ci
npm run build
```
- Build output directory:
  - `dist/spa`

#### Environment Variables (Cloudflare Pages)
- `VITE_API_BASE_URL`
  - Example: `https://<your-render-service>.onrender.com/api`

#### SPA Routing
- This repo includes [frontend/public/_redirects](file:///Users/judeibardaloza/Desktop/Final_MediSync/frontend/public/_redirects) so client-side routes resolve to `index.html`.

### Notes
- The frontend automatically reads `VITE_API_BASE_URL` first, but still supports `localStorage.API_BASE_URL` overrides for debugging.
- For production security, keep `DJANGO_DEBUG=false` and provide explicit `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

