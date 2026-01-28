# Ad Platform MVP

Multi-platform reklam yönetimi ve AI-powered insights platformu.

## 🎯 MVP Scope

**Desteklenen Platformlar:**
- Google Ads
- Meta Ads (Facebook/Instagram)

**Core Features:**
- OAuth ile hesap bağlama
- Günlük metrik senkronizasyonu
- Unified cross-platform dashboard
- AI-powered günlük özet ve öneriler
- Email/WhatsApp alert sistemi

## 🛠️ Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Next.js 14 + TypeScript + Tailwind + shadcn/ui |
| Backend | Python 3.11 + FastAPI |
| Database | Supabase (PostgreSQL) |
| Queue | Celery + Redis |
| AI | OpenAI API (GPT-4o) |
| Hosting | Railway |

## 📁 Proje Yapısı

```
adplatform-mvp/
├── frontend/                 # Next.js frontend
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities & Supabase client
│   │   └── types/           # TypeScript types
│   └── package.json
│
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/             # API routes
│   │   │   ├── auth/        # OAuth endpoints
│   │   │   ├── accounts/    # Account management
│   │   │   ├── metrics/     # Metrics queries
│   │   │   ├── insights/    # AI insights
│   │   │   └── actions/     # Action execution
│   │   ├── connectors/      # Platform connectors
│   │   │   ├── google_ads/  # Google Ads API
│   │   │   └── meta_ads/    # Meta Marketing API
│   │   ├── services/        # Business logic
│   │   │   ├── sync/        # Data sync services
│   │   │   ├── insights/    # AI insight generation
│   │   │   └── notifications/ # Email/WhatsApp
│   │   ├── models/          # Pydantic models
│   │   ├── core/            # Config, security, etc.
│   │   └── tasks/           # Celery tasks
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/                 # SQL migrations
│   ├── 001_initial_schema.sql
│   └── 002_seed_and_helpers.sql
│
├── docker-compose.yml
└── README.md
```

## 🚀 Kurulum

### 1. Supabase Setup

1. [Supabase](https://supabase.com) hesabı oluştur
2. Yeni proje oluştur
3. SQL Editor'da migration dosyalarını çalıştır:
   - `database/001_initial_schema.sql`
   - `database/002_seed_and_helpers.sql`

4. Environment variables'ları al:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

### 2. Platform API Credentials

**Google Ads:**
1. [Google Cloud Console](https://console.cloud.google.com) → Yeni proje
2. Google Ads API'yi etkinleştir
3. OAuth 2.0 credentials oluştur
4. Developer token al (test account için)

**Meta Ads:**
1. [Meta for Developers](https://developers.facebook.com) → App oluştur
2. Marketing API'yi ekle
3. App ID ve App Secret al

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# .env dosyası oluştur
cp .env.example .env
# Değişkenleri doldur

# Development server
uvicorn app.main:app --reload
```

### 4. Frontend Setup

```bash
cd frontend
npm install

# .env.local dosyası oluştur
cp .env.example .env.local
# Değişkenleri doldur

# Development server
npm run dev
```

### 5. Redis & Celery (Background Jobs)

```bash
# Redis başlat (Docker ile)
docker run -d -p 6379:6379 redis:7-alpine

# Celery worker başlat
cd backend
celery -A app.tasks worker --loglevel=info

# Celery beat (scheduler)
celery -A app.tasks beat --loglevel=info
```

## 🔐 Environment Variables

### Backend (.env)
```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx

# Google Ads
GOOGLE_ADS_CLIENT_ID=xxx
GOOGLE_ADS_CLIENT_SECRET=xxx
GOOGLE_ADS_DEVELOPER_TOKEN=xxx
GOOGLE_ADS_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Meta Ads
META_APP_ID=xxx
META_APP_SECRET=xxx
META_REDIRECT_URI=http://localhost:8000/api/auth/meta/callback

# OpenAI
OPENAI_API_KEY=xxx

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=xxx
ENCRYPTION_KEY=xxx  # For token encryption
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Database Schema Overview

### Core Tables
- `organizations` - Multi-tenant organizations
- `users` - User profiles (linked to Supabase Auth)
- `connected_accounts` - OAuth-connected ad accounts

### Campaign Data
- `campaigns` - Synced campaigns
- `ad_sets` - Ad sets / Ad groups
- `daily_metrics` - Daily aggregated metrics
- `hourly_metrics` - Real-time metrics (optional)

### AI & Insights
- `insights` - AI-generated insights
- `recommended_actions` - Actionable recommendations
- `daily_digests` - Daily summary reports

### System
- `sync_jobs` - Background job tracking
- `api_rate_limits` - Rate limit management

## 🔄 Data Flow

```
1. OAuth Connect
   User → Frontend → Backend → Platform OAuth → Store tokens

2. Daily Sync (Celery)
   Scheduler → Fetch metrics → Normalize → Store in Supabase

3. Insight Generation
   Sync complete → Analyze metrics → GPT-4o → Generate insights

4. Daily Digest
   Morning job → Aggregate data → Generate summary → Send notifications
```

## 📱 API Endpoints (Preview)

```
Auth:
  POST   /api/auth/google/initiate
  GET    /api/auth/google/callback
  POST   /api/auth/meta/initiate
  GET    /api/auth/meta/callback

Accounts:
  GET    /api/accounts
  GET    /api/accounts/{id}
  DELETE /api/accounts/{id}
  POST   /api/accounts/{id}/sync

Metrics:
  GET    /api/metrics/summary
  GET    /api/metrics/daily
  GET    /api/metrics/campaigns
  GET    /api/metrics/compare

Insights:
  GET    /api/insights
  GET    /api/insights/{id}
  POST   /api/insights/{id}/read
  POST   /api/insights/{id}/dismiss

Actions:
  GET    /api/actions
  POST   /api/actions/{id}/execute
  POST   /api/actions/{id}/dismiss

Digest:
  GET    /api/digest/today
  GET    /api/digest/history
```

## 🚀 Deployment (Railway)

1. Railway hesabı oluştur
2. GitHub repo'yu bağla
3. Environment variables ekle
4. Deploy!

```yaml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

## 📈 Roadmap

### Phase 1 (MVP) ✅
- [x] Database schema
- [ ] OAuth integration (Google + Meta)
- [ ] Basic metric sync
- [ ] Simple dashboard
- [ ] AI daily digest

### Phase 2
- [ ] Amazon Ads integration
- [ ] Advanced insights
- [ ] One-click actions
- [ ] WhatsApp notifications

### Phase 3
- [ ] TikTok Ads
- [ ] Custom rules/alerts
- [ ] Team collaboration
- [ ] White-label option

## 📝 License

MIT

## 🤝 Contributing

PRs welcome!