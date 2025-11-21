## SalesSpeak - Conversational AI Sales Assistant

SalesSpeak is a voice-first sales copilot that guides shoppers through product discovery with persuasive, context-aware conversations and instant audio feedback.

### Key Features

- Real-time speech-to-text and text-to-speech orchestration
- Groq-hosted large language models tuned for sales dialogues
- Multi-language support with code-switching awareness
- Persistent session memory driven by Supabase and conversation storage
- Modern Next.js interface with live voice streaming components
- Unified logging and health monitoring for production observability

### Architecture

- Backend API (`app/`): FastAPI service that wires authentication, voice pipelines, Supabase state, and assistant orchestration.
- Frontend (`frontend/`): Next.js 15 application providing the live voice UI and analytics views.
- Static assets (`static/audio/`): Persisted audio responses available for download and playback.

### Prerequisites

- Python 3.12+
- Node.js 18+ (PNPM 9 recommended)
- Valid Groq and SerpAPI credentials
- Supabase project credentials (URL, anon key, service role key, database URL)
- Git

## Setup

### 1) Clone the repository

```bash
git clone https://github.com/HACKTHEMM/SaleSpeak.git
cd SaleSpeak
```

### 2) Backend environment

```bash
# (optional) ensure uv is available for dependency syncing
pip install --upgrade uv

# create or refresh the local .venv using uv.lock + pyproject.toml
uv sync

# activate the virtual environment
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

If you prefer plain pip instead of uv, export a requirements file with `uv export --format requirements.txt --output requirements.txt` and then run `pip install -r requirements.txt` inside your virtual environment.

### 3) Environment variables

Create a `.env` file in the repository root aligning with `app/Config.py`:

```env
GROQ_API_KEY=your_groq_api_key
SERP_API_KEY=your_serp_api_key
SUPABASE_DB_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
LOGIN_ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=43200
RESET_PASSWORD_TOKEN_EXPIRE_MINUTES=30
EMAIL_CONFIRMATION_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_SECRET=change_me
ACCESS_TOKEN_SECRET=change_me
SIGNUP_TOKEN_SECRET=change_me
FORGOT_PASSWORD_TOKEN_SECRET=change_me
PORT=8000
BASE_API_V1=/api/v1
MODEL_ID=meta-llama/llama-4-scout-17b-16e-instruct
DEBUG=false
COMPANY_NAME=SaleSpeak
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
```

### 4) Frontend setup

```bash
cd frontend
npm install --force
npm build
cd ..
```

Optional frontend environment (`frontend/.env.local`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
```

## Run

- Backend (development):

  ```bash
  uv run python start.py
  ```

  FastAPI starts on `http://127.0.0.1:8000` with auto-reload and log streaming.

- Frontend (development server):

  ```bash
  cd frontend
  pnpm dev
  ```

  The Next.js app is served on `http://127.0.0.1:3000`.

To run both services simultaneously, start the backend from the project root and the frontend from the `frontend/` directory in a separate terminal.

## API Overview

- **Health check**: `GET /health`
- **Start voice assistant**: `POST /api/v1/voice-assistant/start-assistant/`
- **Transcript echo** (debug): `POST /api/v1/voice-assistant/get-transcript`
- **Fetch generated audio**: `GET /api/v1/voice-assistant/get-audio/{session_id}`
- **Latest response metadata**: `GET /api/v1/voice-assistant/get-latest-response/{session_id}`
- **Session debug info**: `GET /api/v1/voice-assistant/debug-session/{session_id}`
- **Authentication, user, and role management**: prefixed under `/api/v1/auth`, `/api/v1/user`, and `/api/v1/roles`

Sample request:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/voice-assistant/start-assistant/" ^
  -H "Content-Type: application/json" ^
  -d "{\"transcript\": \"Hello, I want to buy a laptop\", \"session_id\": \"test-123\"}"
```

## Project Structure

```
SaleSpeak/
├── README.md
├── pyproject.toml
├── uv.lock
├── start.py
├── schema.sql
├── log.txt
├── static/
│   └── audio/
├── app/
│   ├── Config.py
│   ├── main.py
│   ├── http_exception.py
│   ├── logging.py
│   ├── oauth.py
│   ├── core/
│   │   ├── app_configure.py
│   │   ├── events.py
│   │   ├── assistant/
│   │   │   └── voice_assistant.py
│   │   └── modules/
│   │       ├── adapters/
│   │       ├── embeddings/
│   │       └── llm/
│   ├── database/
│   │   ├── connections/
│   │   │   └── supabase.py
│   │   ├── models/
│   │   │   ├── config.py
│   │   │   ├── roles.py
│   │   │   ├── token.py
│   │   │   ├── transcript.py
│   │   │   └── user.py
│   │   └── repositories/
│   │       ├── roles.py
│   │       ├── session_repository.py
│   │       ├── token.py
│   │       └── user.py
│   ├── routes/
│   │   └── api/
│   │       ├── routers.py
│   │       └── v1/
│   │           ├── auth.py
│   │           ├── roles.py
│   │           ├── user.py
│   │           └── voice_assistant.py
│   ├── schema/
│   │   ├── enums.py
│   │   ├── health.py
│   │   └── token.py
│   └── utils/
│       ├── helper.py
│       ├── logging.py
│       └── uptime.py
└── frontend/
    ├── package.json
    ├── pnpm-lock.yaml
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── chat/page.tsx
    ├── components/
    │   ├── api-status.tsx
    │   ├── voice-recognition.tsx
    │   └── ...
    ├── hooks/
    │   ├── use-mobile.tsx
    │   └── use-toast.ts
    ├── services/
    │   └── custom-voice-api.ts
    └── styles/
        └── globals.css
```

## Troubleshooting

- Update `.env` entries if the server exits during startup; missing Supabase or Groq keys will halt initialization.
- Ensure the backend is running before hitting `/api/v1/voice-assistant/*` endpoints; the assistant instance is configured at startup.
- If PNPM is unavailable, install it with `npm install -g pnpm` or use `npm install` (delete `pnpm-lock.yaml` if mixing package managers).
- Audio playback issues typically mean the `static/audio/` directory lacks generated files; verify the backend log output.

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`.
3. Commit your changes: `git commit -m "Add some amazing feature"`.
4. Push the branch: `git push origin feature/amazing-feature`.
5. Open a Pull Request.

## License

This project is part of the HackThem The Matrix Protocol submission. Refer to the competition guidelines for usage terms.

---

Team HackThem — Building the future of conversational AI for e-commerce decisions.