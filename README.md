## SalesSpeak - Conversational AI Sales Assistant

A conversational agent that helps users make better decisions while buying products online through natural voice interactions and intelligent product recommendations.

### 🌟 Key Features

- **Real-time voice**: Advanced speech-to-text and text-to-speech
- **AI conversations**: Powered by Groq-hosted LLMs
- **Sales-focused tone**: Persuasive and engaging responses
- **Context awareness**: Embeddings and conversation memory with ChromaDB
- **Multi-language**: English, Hindi, and code-switching
- **Modern UI**: Next.js frontend with live voice interaction
- **Robust API**: FastAPI backend with CORS and rich error logs

### 🏗 Architecture

- **Backend API** (`/app`): FastAPI + voice processing + AI
- **Frontend** (`/frontend`): Next.js app and components
- **Inference** (`run_inference.py`): CSV batch QA engine

### 📋 Prerequisites

- **Python 3.8+**
- **Node.js 18+** and **npm**
- **Groq API key** and **SerpAPI key**
- Git

## 🚀 Setup

### 1) Clone

```bash
git clone https://github.com/HACKTHEMM/VoiceBot_HackThem_submission.git
cd VoiceBot_HackThem_submission
```

### 2) Python environment

```bash
# Create venv
python -m venv venv

# Activate
# macOS/Linux
source venv/bin/activate
# Windows (PowerShell)
./venv/Scripts/Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3) Backend environment variables

Create a `.env` file in the project root:

```env
# API Keys
GROQ_API_KEY=your_groq_api_key_here
SERP_API_KEY=your_serpapi_key_here

# Model
MODEL_ID=meta-llama/llama-4-scout-17b-16e-instruct

# Database paths (adjust as needed)
MASTER_DB_PATH=./app/chromadb_storage/master_db
CHILD_DB_PATH=./app/chromadb_storage/conversation_db
```

### 4) Frontend setup

```bash
cd frontend
npm install --force
npm run build
cd ..
```

Optional frontend env (`frontend/.env.local`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here
CLERK_SECRET_KEY=your_clerk_secret_key_here
```

## 🏃‍♂️ Run

### Option A: Full app (backend + frontend)

Runs both servers; handles installs/builds where needed.

```bash
python main.py
```

Backend: `http://localhost:8000`

Frontend: `http://localhost:3000`

### Option B: Backend only

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Option C: Inference (batch CSV)

```bash
# Ensure venv is active
python run_inference.py
```

Generates answers for `test.csv` and writes `output.csv`.

Custom invocation:

```python
from run_inference import run_inferance

run_inferance(
    csv_input_path="./your_questions.csv",
    csv_output_path="./your_responses.csv",
)
```

## 📚 API

### Health

```http
GET /
```

### Start assistant

```http
POST /start-assistant/
Content-Type: application/json

{
  "transcript": "Your voice message text here",
  "session_id": "unique-session-identifier"
}
```

Sample response (fields may vary):

```json
{
  "success": true,
  "text": "AI generated response text",
  "audio_file": "path/to/generated/audio/file.wav",
  "audio_url": "/get-audio/<session_id>",
  "static_audio_url": "/static/audio/<filename>.wav",
  "audio_filename": "<filename>.wav",
  "products": [],
  "message": "Generated response based on transcript",
  "execution_time": {
    "assistant_processing_time": 0.123,
    "total_execution_time": 0.456
  }
}
```

### Transcript echo (testing)

```http
POST /get-transcript
Content-Type: application/json

{
  "transcript": "Test transcript",
  "session_id": "test-session"
}
```

### Get audio file for a session

```http
GET /get-audio/{session_id}
```

### Get latest response metadata

```http
GET /get-latest-response/{session_id}
```

### Debug session

```http
GET /debug-session/{session_id}
```

## 📁 Project structure

```
SalesSpeak/
├── README.md
├── requirements.txt
├── main.py                         # Orchestrates backend + frontend
├── run_inference.py                # Batch inference
├── test.csv                        # Sample questions
├── output.csv                      # Batch outputs
├── .env                            # Backend environment (create)
├── app/
│   ├── main.py                     # FastAPI application
│   ├── core/
│   │   ├── assistant/
│   │   │   └── voice_assistant.py
│   │   └── modules/
│   │       ├── adapters/
│   │       ├── embeddings/
│   │       └── llm/
│   ├── helper/
│   │   ├── config.py
│   │   └── get_config.py
│   ├── models/
│   │   └── transcript.py
│   └── chromadb_storage/
└── frontend/
    ├── package.json
    ├── app/
    ├── components/
    ├── hooks/
    ├── services/
    └── public/
```

## 🔧 Configuration notes

- **LLM**: `MODEL_ID` defaults to `meta-llama/llama-4-scout-17b-16e-instruct` (Groq)
- **STT**: Google Speech-to-Text
- **TTS**: Edge-TTS
- **DB**: ChromaDB for master and per-session memory

## 🧪 Quick testing

```bash
curl http://localhost:8000/

curl -X POST "http://localhost:8000/start-assistant/" \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Hello, I want to buy a laptop", "session_id": "test-123"}'
```

## 🚨 Troubleshooting

- **Missing API keys**: Ensure `.env` has `GROQ_API_KEY` and `SERP_API_KEY` (note the name).
- **Frontend peer deps**: Run `npm install --force` in `frontend/`.
- **Virtualenv issues**: Reactivate the venv and reinstall requirements.
- **Audio device errors**: Grant microphone permissions to your terminal/IDE.
- **Imports fail**: Run commands from the repo root.

## 📊 Usage examples

- **Product inquiries**: "Tell me about your investment platform"
- **Pricing**: "What are the fees for small investments?"
- **Safety**: "Is it safe to invest through your platform?"
- **Comparison**: "How does this compare to other platforms?"

## 🤝 Contributing

1) Fork the repository
2) Create a feature branch: `git checkout -b feature/amazing-feature`
3) Commit: `git commit -m "Add some amazing feature"`
4) Push: `git push origin feature/amazing-feature`
5) Open a Pull Request

## 📝 License

This project is part of the HackThem The Matrix Protocol submission. See competition guidelines for usage terms.

---

Team HackThem — Building the future of conversational AI for e-commerce decisions.