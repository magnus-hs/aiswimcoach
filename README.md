# AI Swim Coach

A comprehensive swim training analytics platform. Upload Garmin `.fit` files from pool swims to get detailed session analysis, AI coaching tips, heart rate tracking, personal best management, structured training plans, and training load analysis.

**Live:** https://main.d3qbayea55l8tl.amplifyapp.com

## Features

### Session Analysis
- **Grouped splits view** — consecutive same-stroke lengths grouped into reps (e.g., 4×25m = 100m) with expandable detail
- **Rest intervals** — rest duration between sets extracted from FIT file idle records
- **Cumulative distance and time** — running totals per rep and across the session
- **Per-length metrics** — time, strokes, stroke type, heart rate, SWOLF

### Performance Charts
- **Heart rate over time** — line chart with time/distance toggle on x-axis
- **SWOLF technique chart** — tracks technique degradation under fatigue with drift detection
- **Efficiency curve** — stroke rate vs pace scatter plot showing your optimal "sweet spot"
- **Training load analysis** — energy system categorization (Sprint/Threshold/Aerobic) with rest-adjusted load scoring

### Training Load & CSS
- **Critical Swim Speed (CSS)** — calculate from 400m/200m time trials, stored in profile
- **Energy system categorization** — each set classified as Sprint, Threshold, or Aerobic relative to CSS
- **Rest-adjusted load** — work-to-rest ratio multiplier accounts for recovery between sets
- **Session load scoring** — quantifies total training stress with per-system breakdown

### Dashboard
- **Activity feed** — chronological list of all swim sessions
- **Distance charts** — weekly (daily bars), monthly (weekly bars), yearly (monthly bars)
- **Clickable chart bars** — filter activity feed by clicking a time period
- **Stats** — total sessions, swims per week/month/YTD, total distance and time

### Personal Bests
- **Structured input** — stroke/distance dropdowns with custom distance support
- **Grouped display** — table format grouped by stroke, distance first
- **Manual vs derived** — entered PBs shown alongside session-derived PBs with comparison
- **Delete support** — remove incorrectly entered PBs

### Training Plans
- **AI-generated multi-week plans** — structured periodization from Bedrock
- **Plan lifecycle** — draft → active → archived with single-active-plan invariant
- **Week/session breakdown** — warm-up, main set, cool-down for each session

### Profile & Settings
- **User profile** — age, nationality, locality, ability level
- **CSS management** — dedicated page with explanation and calculator
- **Profile picture** — upload from the profile section

### AI Coaching
- **Personalized tips** — 3 actionable coaching tips per session from Claude via Bedrock
- **Drill recommendations** — specific drills based on your metrics
- **Ability assessment** — competitive ranking analysis

## Architecture

```
Frontend (React/Vite) → API Gateway → Lambda (Python 3.12) → DynamoDB / S3 / Bedrock
```

- **Frontend:** React 18, TypeScript, Vite, Recharts, plain CSS with design tokens
- **Backend:** Python 3.12 Lambda, fitparse, boto3
- **AI:** Amazon Bedrock (Claude 3.5 Sonnet)
- **Storage:** DynamoDB (sessions, profiles, plans), S3 (FIT files, profile pictures)
- **Hosting:** AWS Amplify (auto-deploy from GitHub main branch)
- **Testing:** pytest + hypothesis (backend), Vitest + fast-check (frontend)

## Project Structure

```
aiswimcoach/
├── backend/
│   ├── handler.py              # Lambda entry point, API routing
│   ├── fit_parser.py           # FIT file parsing (splits, rest intervals, HR)
│   ├── session_history.py      # DynamoDB session persistence
│   ├── pb_resolver.py          # Personal best management
│   ├── plan_lifecycle.py       # Training plan state machine
│   ├── plan_generator.py       # AI plan generation via Bedrock
│   ├── bedrock_client.py       # Bedrock coaching invocation
│   ├── hr_zones.py             # Heart rate zone calculation
│   ├── profile_manager.py      # User profile CRUD
│   ├── models.py               # Dataclasses (Session, Metrics, etc.)
│   └── tests/                  # 359 tests (pytest)
├── frontend/
│   ├── src/
│   │   ├── pages/              # DashboardPage, ActivityDetailPage, CSSPage, etc.
│   │   ├── components/         # GroupedSplitsTable, HRTimeGraph, SwolfChart, etc.
│   │   ├── api/                # Service modules (session, plan, profile, upload)
│   │   ├── utils/              # groupSplits, pbValidation, pbGrouping
│   │   └── types.ts            # Shared TypeScript interfaces
│   └── package.json            # 194 tests (vitest)
└── .kiro/specs/                # Feature specifications
```

## Getting Started

### Prerequisites
- Python 3.12+, Node.js 18+, AWS CLI configured

### Backend
```bash
cd backend
python -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v  # Run tests
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # Development server
npm run build     # Production build
npm run test      # Run tests
```

### Deploy
```bash
# Lambda
bash build-lambda.sh
aws lambda update-function-code --function-name ai-swim-coach --zip-file fileb://backend.zip --region us-east-1

# Frontend (auto-deploys on push to main)
git push origin main
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /upload | Upload FIT file, get coaching + metrics |
| GET | /sessions | List user sessions |
| GET | /sessions/:id | Get session detail (splits, coaching, HR) |
| POST | /personal-bests | Save manual PB |
| GET | /personal-bests | Get all PBs (manual + derived) |
| DELETE | /personal-bests | Remove a PB |
| POST | /profile | Save user profile |
| GET | /profile | Get user profile |
| POST | /profile/css | Save CSS pace |
| GET | /profile/css | Get CSS pace |
| POST | /plans/generate | Generate structured training plan |
| GET | /plans/structured | List all plans |
| GET | /plans/:id | Get plan detail |
| PATCH | /plans/:id/status | Activate/archive plan |

## License

MIT
