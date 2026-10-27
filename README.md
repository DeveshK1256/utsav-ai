# Utsav (उत्सव) — Celebrations, Composed.

Utsav is a culture-native GenAI event planning assistant for weddings, birthdays, and community celebrations in India. It unites visual vibe extraction, formulaic budget scaling, vendor quotation audits, and astronomical panchang guidance into an interactive event workspace with a deterministic, zero-hallucination computational core.

---

## 🌐 Live Production Links

* **Production Web App:** [https://utsav-ai.netlify.app](https://utsav-ai.netlify.app)
* **Backend API:** [https://utsav-ai-ycg2.onrender.com](https://utsav-ai-ycg2.onrender.com)
* **Service Health Check:** [https://utsav-ai-ycg2.onrender.com/health](https://utsav-ai-ycg2.onrender.com/health)
* **Master Architectural Specification:** [`docs/UTSAV_MASTER_DOC.md`](docs/UTSAV_MASTER_DOC.md)

---

## 📊 Project Milestone Status

Status reflected directly from [`docs/UTSAV_MASTER_DOC.md`](docs/UTSAV_MASTER_DOC.md) (Section 17.2):

| Milestone / Capability | Status | Implementation Reality |
| :--- | :--- | :--- |
| **M0: Foundation & Core Data Engine** | **Complete** | Deployed on Render + Netlify. Managed Singapore PostgreSQL with Alembic migrations, DAG task scheduler, deterministic budget scaling by city tier. |
| **M1: F5 Hidden-Cost Detector** | **Complete** | Multimodal vendor quotation extraction with Google Gemini, market benchmark median checks, Devanagari OCR translation, and offline fallback transparency. |
| **M2: F1 Live Replanning Engine** | **Complete** | Deterministic Plan B state machine for guest surges, date moves, and vendor cancellations. Zero LLM math; sequential disruption promotion. |
| **M3: F4 Vibe-to-Plan Studio** | **Complete** | Batched inspiration photo analysis with Gemini vision, deterministic local Pillow (PIL) mood board collage generation, and granular line-item budget acceptance. |
| **Multi-Event Workspace Expansion** | **Complete** | Unified multi-tab dashboard covering Weddings, Birthdays (Carnival, Milestone, Ayushya Homa), and Community Festivals (Navratri, Sarvajanik, Society Mela). |
| **M4: F3 WhatsApp Guest Coordination** | **Paused** | Code-complete backend abstractions (`MetaCloudWhatsAppProvider` & mock provider), send-layer opt-out hard boundary, and FAQ concierge. **Paused pending Meta WhatsApp Business API business verification.** Not tested with real phone numbers. |
| **M5: F2 Cultural & Ritual Intelligence** | **In Progress** | Astronomical Panchang Engine (`ephem` + NOAA solar physics) verified against external astronomical references with zero LLM time math. Tradition content layer is **explicitly AI-drafted and unreviewed** (`is_verified: false` across all 21 database rows). Dual mandatory elevated disclaimers active. |
| **M10: F16 Invitation Card Generator** | **Complete** | Server-side composition via Pillow (DEC-028), Google Noto Sans Devanagari verified for Hindi/Marathi/Sanskrit, zero-placeholder guarantee (DEC-029), single-pipeline dual PNG and 300 DPI PDF export (DEC-030), and partial failure isolation for guest batches. |
| **F15-Lite: Venue Discovery (Stage 3)** | **Complete** | Curated real directory seed set (19 venues: 11 Jaipur, 8 Pune) with locality-centroid coordinates, non-blocking geolocation flow with manual fallback, and strict honesty guardrails (`rating_tier: new_unrated`, `limited_data: true`, DEC-031). |
| **Stage 4: Compose Celebration Orchestration** | **Complete** | Coherent guided flow sequencing Venue Selection -> Muhurat Timing -> Invitation Generation. Zero assumption inheritance (DEC-032), shortlist-pick venue tracking, deterministic muhurat locking, and clean unconfirmed placeholders in invitation outputs. |
| **M6–M9: Future Capabilities (F6–F15 Full)** | **Specced** | Risk Forecaster, Seating Solver, Offline PWA, and full Leaflet/PostGIS Venue Map (F15) specced in roadmap; not yet built. |

---

## 🛠️ Technology Stack

* **Frontend:** Next.js 16 (App Router, Static Export to Netlify Edge), React 19, TypeScript, Tailwind CSS, Lucide Icons.
* **Backend API:** FastAPI (Python 3.12/3.14), Uvicorn, SQLAlchemy, Alembic, Pydantic v2.
* **Database:** Managed PostgreSQL 16 (Singapore region on Render).
* **AI & LLM Services:** Google Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`) for multimodal ingestion, quotation extraction, and cross-cultural tradition merging, backed by deterministic offline stubs for testing.
* **Astronomical Engine:** `ephem` (PyEphem) orbital mechanics and solar geometry models with Chitrapaksha (Lahiri) Ayanamsha for deterministic panchang and muhurat windows.
* **Graphic Generation:** Pure Pillow (PIL) for deterministic 1200×800 mood board collages and 1200×1800 personalized invitation cards (PNG + 300 DPI PDF) without generative model dependencies. Official Google Noto Sans Devanagari bundled for Marathi/Hindi typography.

---

## ⚠️ Known Limitations & Honest Caveats

1. **Tradition & Ritual Content is Unverified AI Drafts:** Ceremony schedules, ritual steps, and samagri item checklists were drafted by AI as starting baselines. **None of the 21 tradition rows have been reviewed by community elders, priests, or liturgical authorities.** All rows are stored with `is_verified: false`. Users must review all sequences with their family elders and officiants before booking or printing invitations.
2. **Panchang & Muhurat Variance:** Auspicious windows and Rahu Kaal calculations are computed using modern Drik Ganita orbital ephemeris formulas. Regional print almanacs (Kalnirnay, Vakya, Surya Siddhanta) often differ by 10–20 minutes due to differing local horizon, elevation, and atmospheric refraction models.
3. **WhatsApp Messaging is Paused:** While the send pipeline, webhook verification, and opt-out blocklist exist in code, Utsav does not yet send real WhatsApp messages. Live guest coordination is paused pending Meta Business compliance approval.
4. **Render Free-Tier Cold Starts:** The backend runs on Render's managed tier. If idle, initial requests may experience a cold-start delay of 45–60 seconds before returning `200 OK`.

---

## 💻 Local Development Setup

### 1. Prerequisites
* Python >= 3.11
* Node.js >= 20.x, npm >= 10.x
* Git

### 2. Clone Repository
```bash
git clone https://github.com/DeveshK1256/utsav-ai.git
cd utsav-ai
```

### 3. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 4. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### 5. Environment Variables
Create a `.env` file in `backend/` (or set environment variables in your shell). **Never commit credentials.**

Required variables:
* `DATABASE_URL` — PostgreSQL connection string (or SQLite path for local exploration, e.g. `sqlite:///./test.db`)
* `GEMINI_API_KEY` — Google Gemini API key (optional for core tests; offline deterministic stubs activate automatically when omitted)
* `PORT` — API port (defaults to `8000`)
* `ENABLE_M4_WHATSAPP` — WhatsApp feature flag (defaults to `false`)

### 6. Run Automated Test Suite & Quality Gates
The repository enforces a strict, zero-tolerance quality and verification pipeline:

#### Full Test Suite & Coverage (140+ tests, >=90% Line Coverage)
All 140+ automated tests run 100% deterministically offline with stubs (zero network calls, zero token consumption):
```bash
pytest tests/ --cov=backend/app --cov-report=term
```

#### CI Quality Ratchet (Zero-Tolerance Enforcement)
Linters and typecheckers enforce a ratchet baseline that strictly improves over time:
```bash
# Python Ruff linter (0 errors enforced)
python -m ruff check backend/

# Python MyPy strict typecheck (0 errors enforced)
python scripts/ci_ratchet.py mypy

# Frontend ESLint (0 errors, 0 warnings)
npm --prefix frontend run lint

# Production Frontend Build
npm --prefix frontend run build
```

#### Dependency Vulnerability Audits
```bash
# Python dependencies audit
python -m pip_audit -r backend/requirements.txt

# Frontend dependencies audit
npm --prefix frontend audit
```

#### Automated Accessibility Scans (Axe-core WCAG 2.2 AA)
```bash
# Verify 0 accessibility violations across core routes
node scripts/audit_axe_playwright.cjs
```

#### End-to-End User Journey Verification
```bash
# Verify 5-step user journey (Onboarding -> Budget Scaling -> Vibe Collage -> Muhurat -> Invitation)
node tests/e2e/test_main_user_journey.cjs
```

### 7. Google Services & Cloud Run Deployment
For production deployment on Google Cloud Run and Google Maps/Gemini integration architecture, consult:
* [`docs/GOOGLE_SERVICES_ARCHITECTURE.md`](docs/GOOGLE_SERVICES_ARCHITECTURE.md) — Google Cloud Run containerization, Cloud Build CI/CD, Secrets Manager, and Gemini Multimodal APIs.

### 8. Run Locally
```bash
# Terminal 1: Backend API
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2: Frontend
npm run dev --prefix frontend
```
Visit `http://localhost:3000` in your browser.

---

## 📜 Cultural Trust & Officiant Disclaimers

> **Ceremony Content Notice:**  
> *Ceremonial timelines and ritual samagri lists provided by Utsav are AI-drafted starting baselines. They have NOT been reviewed by priests or community elders. Always review your run-of-show with family elders and your officiating priest (Panditji / Guruji / Qazi / Pastor) to honor your family's specific lineage customs (Kul-Parampara).*

> **Panchang Astronomical Notice:**  
> *Panchang timings (Sunrise, Sunset, Rahu Kaal, Tithi, Nakshatra, and Muhurat windows) are mathematical calculations based on Drik Ganita and Ephemeris models for venue coordinates. Always verify final auspicious timings with your family priest.*

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
