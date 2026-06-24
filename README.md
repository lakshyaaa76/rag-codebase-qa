# RAG Codebase Q&A

A full-stack application that allows users to ask natural-language questions about any GitHub repository using Retrieval-Augmented Generation (RAG).

## Features

- 🔍 **Index GitHub Repositories** — Clone and analyze any public GitHub repository
- 🤖 **Natural Language Queries** — Ask questions about the codebase in plain English
- 💾 **Vector Embeddings** — Store code embeddings in Supabase for fast retrieval
- 🧠 **AI-Powered Answers** — Use Grok AI to generate contextual answers with citations
- 🔗 **Citation Support** — Get references to the exact files and lines in the source code
- ⚡ **Real-time Status** — Monitor indexing progress with live status updates

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **LLM**: Grok API (xAI)
- **Vector DB**: Supabase (PostgreSQL + pgvector)
- **Server**: Uvicorn
- **Dependencies**: Pydantic, httpx, python-dotenv

### Frontend
- **Framework**: Next.js 15 with React 19
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **HTTP Client**: Built-in fetch API

### External Services
- **GitHub**: Repository cloning and code retrieval
- **Supabase**: Vector storage and semantic search
- **Grok AI**: LLM for answer generation

## Prerequisites

- Python 3.13+
- Node.js 18+
- npm or yarn
- Git
- API Keys:
  - Supabase (URL + Key)
  - GitHub Token (for private repos and rate limits)
  - Grok API Key (xAI)

## Installation

### 1. Clone the Repository
```bash
git clone <repo-url>
cd rag-codebase-qa
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# --- Supabase ---
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# --- GitHub ---
GITHUB_TOKEN=your_github_token

# --- Grok ---
GROK_API_KEY=your_grok_api_key
GROK_MODEL=grok-3
GROK_MAX_TOKENS=1024
GROK_TEMPERATURE=0.2

# --- Retrieval ---
RETRIEVAL_TOP_K=5
MAX_FILES_PER_REPO=500

# --- CORS ---
ALLOWED_ORIGINS=http://localhost:3000

# --- Frontend ---
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
# or
source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Backend (from `backend/` directory)
```bash
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### Frontend (from `frontend/` directory)
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Verify Backend Health
```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

## Project Structure

```
rag-codebase-qa/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration & settings
│   ├── database.py         # Database connection
│   ├── requirements.txt    # Python dependencies
│   ├── llm/
│   │   └── grok.py        # Grok API integration
│   ├── models/
│   │   └── schemas.py     # Pydantic models
│   ├── routers/
│   │   ├── query.py       # Query endpoint
│   │   └── repos.py       # Repository management
│   ├── services/
│   │   ├── chunker.py     # Code chunking
│   │   ├── embedder.py    # Embedding generation
│   │   ├── indexer.py     # Repository indexing
│   │   ├── ingestion.py   # Data ingestion pipeline
│   │   └── retriever.py   # Vector retrieval
│   └── utils/
│       ├── file_filter.py # File filtering logic
│       └── github.py      # GitHub API utilities
├── frontend/               # Next.js frontend
│   ├── app/
│   │   ├── page.tsx       # Home page
│   │   └── repo/          # Repository pages
│   ├── components/        # React components
│   ├── lib/              # Utility functions
│   ├── types/            # TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── database/
│   └── 001_initial_schema.sql
├── .env                   # Environment variables
├── .gitignore
└── README.md
```

## API Endpoints

### Health Check
- **GET** `/health` — Check backend status
  - Response: `{"status": "ok"}`

### Repository Management
- **POST** `/repos/index` — Index a GitHub repository
- **GET** `/repos/{repoId}/status` — Get indexing status

### Query Endpoint
- **POST** `/query` — Submit a question about a codebase
  - Request: `{"repository_url": "...", "question": "..."}`
  - Response: `{"answer": "...", "citations": [...]}`

## Development Notes

### Environment Files
- `.env` — Shared configuration (backend + frontend via NEXT_PUBLIC_ prefix)
- `frontend/.env.local` — Frontend-only overrides (git-ignored)

### Database
Initialize the schema:
```bash
psql -h <supabase-host> -U postgres -d postgres -f database/001_initial_schema.sql
```

### Adding Dependencies
**Backend:**
```bash
cd backend
.venv\Scripts\pip install <package>
pip freeze > requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install <package>
```

## Troubleshooting

### Backend won't start
- Ensure all environment variables are set in `.env`
- Check Python version: `python --version` (need 3.13+)
- Verify virtual environment is activated

### Frontend won't connect to backend
- Ensure `NEXT_PUBLIC_API_URL` is correct in `.env`
- Check backend is running on port 8000
- Verify CORS settings in backend config

### JSON encoding errors
- Ensure `.env` files are UTF-8 encoded (not UTF-8 with BOM)
- Use `"use client"` directive in Next.js components with event handlers

## License

MIT
