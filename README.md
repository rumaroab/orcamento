# Budget Explorer MVP

A web application that makes government budget PDFs easier for ordinary citizens to understand. The app extracts budget line items from PDFs, categorizes them, and provides explanations with evidence.

## Features

- **Upload Budget PDFs**: Upload one PDF per year (e.g., 2023, 2024, 2025)
- **Automatic Extraction**: Extracts text from PDFs and identifies sections
- **LLM-Powered Processing**: Uses configurable LLM providers (OpenAI, Ollama) to extract, categorize, and explain budget items
- **Simple Taxonomy**: 5 revenue categories and 8 expense categories
- **Evidence-Based**: Every item includes source page number and literal excerpt
- **Drill-Down Navigation**: Browse by categories and view individual items
- **PDF Source Links**: View original PDF at the relevant page

## Tech Stack

### Backend
- **FastAPI**: REST API
- **Celery + Redis**: Background job processing
- **SQLAlchemy + Alembic**: Database ORM and migrations
- **PostgreSQL**: Database
- **PyMuPDF (fitz)**: PDF text extraction
- **LLM Providers**: Provider-agnostic LLM interface supporting:
  - **OpenAI** (GPT-4, GPT-3.5) - Full LLMs
  - **Ollama** (Llama2, Mistral, etc.) - Local SLMs
  - **Disabled** - For debugging without LLM calls

### Frontend
- **Next.js 14** (App Router): React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling

## Project Structure

```
orcamento/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database setup
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── pdf_parser.py        # PDF extraction & sectioning
│   │   ├── tasks.py             # Celery tasks
│   │   └── llm/
│   │       ├── __init__.py
│   │       └── client.py        # LLM client
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router
│   │   ├── page.tsx             # Home page
│   │   ├── documents/[id]/      # Document dashboard
│   │   ├── documents/[id]/category/[category]/  # Category view
│   │   └── items/[id]/          # Item detail
│   ├── package.json
│   └── Dockerfile
├── storage/                     # Uploaded PDFs (created automatically)
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- LLM Provider (choose one):
  - OpenAI API key (for full LLMs)
  - Ollama installed locally (for local SLMs)
  - Or set `LLM_DISABLED=true` for testing without LLM

### Step 1: Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-key-here
```

### Step 2: Start Services

Start all services with Docker Compose:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Celery worker
- Frontend (port 3000)

### Step 3: Run Database Migrations

Run Alembic migrations to create database tables:

```bash
docker-compose exec backend alembic upgrade head
```

If you need to create a new migration:

```bash
docker-compose exec backend alembic revision --autogenerate -m "Description"
docker-compose exec backend alembic upgrade head
```

### Step 4: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

### Upload a Document

1. Go to http://localhost:3000
2. Enter the year (e.g., 2023)
3. Select a PDF file
4. Click "Upload"

The document will be processed in the background. You can see progress on the document dashboard.

### View Results

1. Click on a document to see the summary dashboard
2. Click on a category to see all items in that category
3. Click on an item to see details, explanation, and evidence
4. Click "View Source PDF" to see the original document at the relevant page

## Development

### Running Locally (Without Docker)

#### Backend

1. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (create `.env` file or export):
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/budget_db
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=your-key-here
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the API:
```bash
uvicorn app.main:app --reload
```

6. Start Celery worker (in another terminal):
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

#### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

3. Start development server:
```bash
npm run dev
```

## Debugging

### LLM Provider Configuration

The application supports multiple LLM providers:

**OpenAI (Full LLM)**
- Best for production with high accuracy
- Requires API key and internet connection
- Models: GPT-4, GPT-3.5, etc.
- Configuration:
  ```bash
  LLM_PROVIDER=openai
  OPENAI_API_KEY=your-key-here
  OPENAI_MODEL=gpt-4-turbo-preview
  ```

**Ollama (Local SLM)**
- Run models locally, no API costs
- Good for development and testing
- Requires Ollama installed locally
- Models: Qwen2.5:3b-instruct (recommended), Llama2, Mistral, CodeLlama, Phi, etc.
- Configuration:
  ```bash
  LLM_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=qwen2.5:3b-instruct
  ```
- Setup:
  ```bash
  # Install Ollama from https://ollama.ai
  # Pull Qwen2.5:3b-instruct (recommended - good balance of speed and accuracy)
  ollama pull qwen2.5:3b-instruct
  # Or other models:
  ollama pull llama2
  ollama pull phi
  ollama pull mistral
  ```
- **Note**: Instruction-tuned models (like qwen2.5:3b-instruct) automatically use the chat API for better structured output. The provider auto-detects this based on model name.

**Disabled (No LLM Calls)**
- Skip LLM calls entirely for debugging
- Configuration:
  ```bash
  LLM_PROVIDER=disabled
  # or
  LLM_DISABLED=true
  ```
- In disabled mode:
  - Pages and sections are still extracted
  - Budget items are not extracted (empty results)
  - No LLM API calls are made

### View Logs

```bash
# Backend logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f celery-worker

# All logs
docker-compose logs -f
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d budget_db
```

### Debug Endpoints

- `GET /api/documents/{id}/pages/{page_number}`: View raw extracted text for a page
- `GET /api/documents/{id}/import-jobs`: View processing job status

## API Endpoints

### Documents
- `POST /api/documents/upload`: Upload a PDF
- `GET /api/documents`: List all documents
- `GET /api/documents/{id}`: Get document details
- `GET /api/documents/{id}/summary`: Get summary statistics
- `GET /api/documents/{id}/pdf`: Serve PDF file
- `GET /api/documents/{id}/pages/{page_number}`: Get page text (debug)

### Categories
- `GET /api/documents/{id}/categories/{category}`: Get items for a category

### Items
- `GET /api/items/{id}`: Get item details

## Database Models

- **Document**: Uploaded PDF metadata
- **Page**: Extracted text per page
- **Section**: Document sections with breadcrumb paths
- **BudgetItem**: Extracted line items with categorization and explanation
- **ImportJob**: Background job status

## Taxonomy

### Revenue (5 categories)
1. Personal taxes
2. Corporate taxes
3. Taxes on purchases
4. Social security contributions
5. Other revenue

### Expenses (8 categories)
1. Health
2. Education
3. Pensions & social support
4. Running the government
5. Security & defense
6. Justice
7. Infrastructure & environment
8. Public debt

## Important Notes

- **No Computed Totals**: The LLM does NOT compute totals. All calculations happen in code from stored values.
- **Evidence Required**: Every item must have `pageNumber` and `evidenceText` (literal excerpt).
- **Unit Normalization**: Values are normalized to EUR for comparisons, but original units are preserved.
- **Deterministic Processing**: Section detection uses heuristics (not perfect, but debuggable).

## Troubleshooting

### PDF Extraction Fails
- Ensure PDFs are text-based (not scanned images)
- Check logs for PyMuPDF errors

### LLM Calls Fail
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota/limits
- Review logs for error messages

### Database Connection Issues
- Ensure PostgreSQL is running
- Check `DATABASE_URL` environment variable
- Verify migrations have run

### Celery Tasks Not Processing
- Ensure Redis is running
- Check Celery worker logs
- Verify `REDIS_URL` is correct

## License

This is an MVP project for demonstration purposes.

