# RuleForge Backend

A Python backend service for contract summarization and rule generation using AI models.

## Features

- 📄 **Document Upload**: Support for PDF, DOCX, and TXT files
- 🤖 **Contract Summarization**: Using Hugging Face transformers (free models)
- 📋 **Rule Generation**: Extract business rules using OpenAI/Google Cloud (free tiers)
- 🗄️ **Document Storage**: SQLite database for documents and generated content
- 🚀 **FastAPI**: High-performance API with automatic documentation

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (running on localhost:5432)
- pip

### PostgreSQL Setup

1. Install PostgreSQL if not already installed
2. Start PostgreSQL service  
3. Create the 'ruleforge' database
4. Make sure your PostgreSQL user has permission to create databases

**📋 Detailed setup instructions: See [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)**

**Database Configuration:**
- Host: localhost
- Port: 5432
- Database: ruleforge
- Username: postgres
- Password: 040202005173

### Installation

1. Clone the repository:
```bash
cd ruleforge-be
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL database:
```bash
# The database will be created automatically when you run the app
# Or manually create it:
python setup_db.py
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys (database settings are pre-configured)
```

6. Run the application:
```bash
python main.py
```

## API Documentation

Once running, visit:
- API Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Free Tier Setup

### OpenAI (Free Trial)
1. Sign up at https://platform.openai.com/
2. Get $5 free credits for new accounts
3. Add your API key to `.env`

### Google Cloud AI (Free Tier)
1. Create account at https://cloud.google.com/
2. Enable Vertex AI API
3. Get free monthly quotas
4. Add your API key to `.env`

### Hugging Face (Always Free)
1. Models run locally - no API key needed
2. Uses transformer models like BART for summarization

## Project Structure

```
ruleforge-be/
├── app/
│   ├── api/            # API endpoints
│   ├── core/           # Configuration
│   ├── models/         # Database models
│   ├── services/       # Business logic
│   └── utils/          # Utilities
├── uploads/            # Document uploads
├── tests/              # Test files
└── main.py            # Application entry point
```

## Development

Run tests:
```bash
pytest
```

Run with auto-reload:
```bash
uvicorn main:app --reload
```