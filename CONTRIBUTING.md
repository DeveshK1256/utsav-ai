# Contributing to Utsav

Thank you for your interest in contributing to **Utsav** — the culture-native AI event planning platform for Indian celebrations.

## Development Workflow

### Prerequisites
- Python 3.12+
- Node.js 20+
- SQLite or PostgreSQL

### Local Backend Setup
```bash
# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn backend.app.main:app --reload --port 8000
```

### Local Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Quality Gates & Verification

Before submitting any Pull Request, ensure all mandatory quality gates pass locally:

1. **Python Linting & Formatting:**
   ```bash
   ruff check backend
   ruff format --check backend
   ```

2. **Static Type Checking:**
   ```bash
   mypy backend
   ```

3. **Backend Unit & Regression Tests:**
   ```bash
   pytest tests --cov=backend/app --cov-branch --cov-fail-under=90
   ```

4. **Frontend Checks:**
   ```bash
   cd frontend
   npm run lint
   npx tsc --project tsconfig.json --noEmit
   npm test
   npm run build
   ```

5. **Security Scan:**
   ```bash
   bandit -r backend/app -q
   ```

## Commit Message Guidelines
Follow conventional commit standards:
- `feat(scope): add new feature`
- `fix(scope): resolve bug`
- `refactor(scope): internal restructuring without behavioral changes`
- `test(scope): add or improve tests`
- `docs(scope): documentation updates`
