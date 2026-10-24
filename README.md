<<<<<<< HEAD
# Crafty Art SEO Management Dashboard

A production-oriented SEO management and monitoring web application designed specifically for **Crafty Art**. It aggregates page-level Google Search Console (GSC) metrics, provides **28-day vs previous 28-day comparison reporting**, enables category and landing page ownership isolation between Managers and Team Leaders, and features an automated **SEO Anomaly & Traffic Decline Alert Engine**.

---

## 1. System Architecture

```
Crafty Art SEO Management Dashboard
├── frontend/                     # React 19 + TypeScript + Vite + Tailwind CSS v4 + Recharts
│   ├── src/
│   │   ├── context/              # Authentication & User State Context
│   │   ├── components/           # Sidebar, Header, StatCards, Recharts Area/Line charts, Badges
│   │   ├── pages/                # Manager & Leader Dashboards, Categories, Pages, Alerts, GSC, Logs
│   │   ├── services/             # Typed API Client with JWT authorization interceptors
│   │   └── types/                # Complete TypeScript domain interfaces
├── backend/                      # Python FastAPI modular application
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py           # JWT Authentication, Manager & Team Leader RBAC dependencies
│   │   │   └── routes/           # Auth, Users, Categories, Pages, Dashboard, Alerts, GSC API routes
│   │   ├── core/                 # Config (Pydantic), Security (bcrypt & PyJWT), Database, Scheduler
│   │   ├── models/               # SQLAlchemy 2.0 ORM Models
│   │   ├── schemas/              # Pydantic v2 validation models
│   │   └── services/             # GSC OAuth & API client, 28-day metric comparison, Alert engine, Demo seeder
│   ├── alembic/                  # Database migration scripts
│   └── requirements.txt          # Python production dependencies
└── tests/                        # Automated Pytest suite (Auth, RBAC, Categories, Calculations, Alerts)
```

---

## 2. Key Features

### User Roles & Backend-Enforced Permissions
- **Manager**:
  - Full system oversight: view all leaders, categories, landing pages, and aggregate metrics.
  - Team management: create, edit, activate, or deactivate team leader accounts.
  - Category authority: create categories and reassign category ownership.
  - Threshold configuration: customize alert thresholds and traffic filters.
  - Synchronization: trigger manual syncs, view execution logs, and connect GSC properties.
- **Team Leader**:
  - Category control: create and manage categories assigned to them.
  - URL mapping: add, check duplicates, and remove landing pages from their categories.
  - Performance monitoring: view read-only performance data across categories, and inspect page-level trends for their assigned categories.
  - **Ownership Isolation**: Backend strictly blocks team leaders from editing, deleting, or reassigning categories or pages belonging to other leaders (`403 Forbidden`).

### 28-Day vs Previous 28-Day Performance Comparison
- Compares the latest 28 complete days available in GSC with the immediately preceding 28 complete days.
- **Impression-Weighted Average Position**: Calculated as $\frac{\sum(\text{Position} \times \text{Impressions})}{\sum \text{Impressions}}$ to prevent low-impression noise from skewing rankings.
- **Category Totals**: Aggregates clicks and impressions from uniquely mapped pages.
- **URL Normalization**: Strips tracking parameters (`utm_*`, `gclid`, `fbclid`), trailing slashes, and anchors to guarantee consistent GSC matching.
- **Cross-Category Mapping Warning**: Warns when a URL is mapped to multiple categories to prevent double counting.

### Automated SEO Decline Alert Engine
- Evaluates pages automatically upon daily sync or on-demand:
  - **Click Decline Warning**: Clicks decrease by $\ge 10\%$.
  - **Click Decline Critical**: Clicks decrease by $\ge 20\%$.
  - **Visibility Warning**: Impressions decrease by $\ge 20\%$.
  - **Ranking Warning**: Average position worsens by $\ge 3.0$ spots.
- **Noise Reduction Filters**: Configurable minimum previous clicks (default: 5) and impressions (default: 25) prevent noisy alerts on negligible traffic.
- **Deduplication**: Prevents duplicate active alerts for the same rule, URL, and comparison window.

### Google Search Console Integration & Demo Data Mode
- Google OAuth 2.0 authorization using read-only scope:
  `https://www.googleapis.com/auth/webmasters.readonly`
- Server-side OAuth exchange keeping refresh tokens and secrets out of browser code.
- Supports both **Domain properties** (`sc-domain:craftyartapp.com`) and **URL-prefix properties**.
- **Transparent Demo Mode**: In development environments without Google OAuth credentials, realistic synthetic Crafty Art data (56 days of daily metrics, 4 categories, 2 leaders, alerts) can be seeded with a single click, clearly tagged as `[DEMO DATA]` so it is never confused with production data.

---

## 3. Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+

### Setup Instructions

1. **Clone and Setup Backend**:
   ```bash
   # Create and activate virtual environment (optional)
   python -m venv venv
   # Windows: venv\Scripts\activate | Unix: source venv/bin/activate

   # Install dependencies
   pip install -r backend/requirements.txt

   # Configure environment variables
   cp .env.example .env
   ```

2. **Run Backend Service**:
   ```bash
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   FastAPI API docs will be available at: `http://127.0.0.1:8000/docs`

3. **Install & Run Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The dashboard UI will launch at: `http://localhost:5173`

---

## 4. Initial Setup & Demo Credentials

When opening the web application for the first time:
1. Navigate to `http://localhost:5173`.
2. The application detects a fresh database and redirects to the **Initial Manager Setup** (`/setup`).
3. Create your administrator account (e.g. `manager@craftyart.com` / `Manager@2026`).
4. Upon submission, the database is initialized, and a complete Crafty Art demo dataset is seeded automatically.

### Pre-Configured Test Accounts:
- **Manager**: `manager@craftyart.com` / `Manager@2026`
- **Team Leader 1**: `priya.sharma@craftyartapp.com` / `TeamLeader@2026`
- **Team Leader 2**: `rahul.verma@craftyartapp.com` / `TeamLeader@2026`

---

## 5. Automated Tests

Run the complete test suite:
```bash
python -m pytest tests/ -v
```
Test coverage includes:
- `test_auth.py`: Initial manager onboarding, duplicate protection, JWT login, authentication status.
- `test_categories.py`: Ownership isolation, RBAC write restrictions, duplicate URL check, cross-category warnings.
- `test_metrics_calculation.py`: URL normalization, 28-day comparison algorithm, impression-weighted average position calculation.
- `test_alerts.py`: Critical/warning threshold detection, noise filters, and active alert deduplication.

---

## 6. Production Deployment Notes

1. **Database**: Update `DATABASE_URL` in `.env` to your managed PostgreSQL instance:
   `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname`
2. **Security**: Generate a cryptographically secure `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Google OAuth 2.0**: In Google Cloud Console:
   - Enable **Google Search Console API**.
   - Create OAuth 2.0 Web Application credentials.
   - Set Authorized Redirect URI: `https://your-domain.com/gsc-connection`.
   - Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
4. **Scheduler**: The background sync runs via APScheduler daily at 03:00 UTC. Ensure worker or container process persists.
=======
# crafty-art-seo-dashboard
invitation category traffice maker
>>>>>>> b1e2cd1b609f80e1a3ce9440f28e9666a9fbab4d
