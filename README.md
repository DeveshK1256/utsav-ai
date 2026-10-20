# Utsav (उत्सव) — Celebrations, Composed.

[![CI Loop Test Gate](https://github.com/DeveshK1256/utsav-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/DeveshK1256/utsav-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-amber.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **Utsav** (उत्सव — Hindi/Sanskrit for "celebration / festival") is the intelligent, culture-native, multimodal GenAI event orchestration platform purpose-built for the logistics, emotional stakes, and traditions of modern Indian celebrations. From multi-day weddings to sacred pujas and community festivals, Utsav combines visual moodboard ingestion, WhatsApp-native guest coordination, and hidden-cost quote audits with a deterministic, zero-hallucination computational core (OR-Tools constraint solvers, astronomical panchang algorithms, and formulaic budget scaling).

---

## 📖 Master Specification & Blueprint
The single authoritative blueprint covering Product Requirements (PRD), System Architecture, 10 Discrete AI Agents, ER Schemas, API Contracts, UI/UX Design System, and Phased Roadmap is located at:
👉 **[`docs/UTSAV_MASTER_DOC.md`](./docs/UTSAV_MASTER_DOC.md)**

---

## ⚡ Core Value Propositions & Pillars
1. **Live Replanning Engine ("Plan B"):** Real-time constraint solver (Google OR-Tools CP-SAT) that shifts downstream schedules, reallocates indoor spaces, and broadcasts vendor adjustments upon weather or ceremony delays in < 3.5s.
2. **Cultural & Ritual Intelligence:** Deep ritual knowledge graph across 12+ Indian traditions (Maharashtrian, Gujarati, Vedic, South Indian, Marwari, etc.) with itemized samagri checklists, auspicious muhurat calculations via Swiss Ephemeris (`pyswisseph`), and an elder-verification disclaimer layer.
3. **WhatsApp-Native Guest Concierge:** Zero-app-download guest coordination via Meta WhatsApp Business Cloud API. Automated invitations, one-tap RSVPs, dietary capture, and real-time FAQ answers.
4. **Hidden-Cost Detector & Negotiation Engine:** Multi-quote OCR comparison matrix that identifies missing GST, diesel generator fuel clauses, midnight overtime rates, and unitemized labor lines, drafting respectful, culturally astute negotiation messages.
5. **Vibe-to-Plan Multimodal Studio:** Computer vision pipeline analyzing Instagram and Pinterest moodboards to extract 6-point color palettes (hex + CSS vars), floral varieties, and realistic fabrication cost estimates.
6. **Day-of Command Mode:** High-contrast, battery-efficient mobile cockpit for coordinators with minute-by-minute run-of-show, delay sliders (+15m/+30m), one-tap vendor dialer, and offline PWA synchronization.

---

## 🛠️ Technology Stack
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Shadcn UI, Framer Motion, Workbox PWA.
- **Compute & AI Services:** FastAPI (Python 3.14), Google OR-Tools CP-SAT, Swiss Ephemeris (`pyswisseph`), Pydantic v2.
- **Realtime & Webhooks:** Node.js 24, NestJS, BullMQ, WebSockets.
- **Databases & Cache:** PostgreSQL 16 with `pgvector`, Redis 7 Cluster.
- **Integrations:** Meta WhatsApp Business Cloud API, Open-Meteo API.

---

## 🚀 Quickstart & Setup Placeholder

### Prerequisites
- Node.js >= 20.x, npm >= 10.x
- Python >= 3.12, `uv` or `pip`
- Docker & Docker Compose (for PostgreSQL & Redis)

### Development Setup
```bash
# Clone the repository
git clone https://github.com/DeveshK1256/utsav-ai.git
cd utsav-ai

# Python Virtual Environment & Test Dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements-test.txt

# Run Automated Verification & Loop Tests
pytest tests/unit tests/schema -v
```

---

## 🧪 Loop Testing Gates & Quality Assurance
Utsav enforces strict automated loop testing gates in CI:
- **Unit Tests:** `tests/unit/` (Budget math, DAG scheduler, phone normalization, seating constraints)
- **Schema Validation Tests:** `tests/schema/` (Pydantic & JSON Schema validation for all 10 agent payloads)
- **Prompt Regression Fixtures:** `tests/prompt-regression/`
- **Evaluation Corpus:** `tests/eval/` (30-50 golden Indian celebration test cases)

---

## 📜 Cultural Trust Disclaimer
> *Auspicious timings & ritual checklists are algorithmic estimates. Please verify with your family Guruji or elders.*
