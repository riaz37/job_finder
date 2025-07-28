# AI Job Agent

An intelligent job application system that automates the entire job search and application process using AI.

## Features

- **Resume Upload & Parsing**: Upload resumes in PDF, DOC, or DOCX format with AI-powered parsing
- **Job Search Automation**: Automatically search for relevant jobs across multiple platforms using JobSpy
- **Resume Customization**: AI-powered resume optimization for specific job applications
- **Cover Letter Generation**: Personalized cover letters for each application
- **Application Tracking**: Comprehensive dashboard to track application status and metrics
- **User Preferences**: Configurable job search criteria and automation settings

## Technology Stack

- **Backend**: FastAPI with Python
- **Frontend**: Streamlit
- **Database**: PostgreSQL with Prisma ORM
- **Cache**: Redis
- **AI**: LangChain, LangGraph, Google Gemini
- **Vector Database**: Pinecone
- **Job Scraping**: JobSpy

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd ai-job-agent
   ```

2. **Install dependencies**:
   ```bash
   make install
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Setup database**:
   ```bash
   make db-generate
   make db-push
   ```

5. **Run the application**:
   ```bash
   # Terminal 1: Run FastAPI backend
   make api
   
   # Terminal 2: Run Streamlit frontend
   make streamlit
   ```

## Development

- FastAPI backend runs on: http://localhost:8000
- Streamlit frontend runs on: http://localhost:8501
- API documentation: http://localhost:8000/docs

## Project Structure

```
ai-job-agent/
├── app/                    # FastAPI backend
│   ├── api/               # API routes
│   ├── core/              # Core configuration
│   ├── db/                # Database connection
│   ├── models/            # Pydantic models
│   └── services/          # Business logic
├── streamlit_app/         # Streamlit frontend
├── prisma/                # Database schema
├── jobspy/                # Job scraping library
└── requirements.txt       # Python dependencies
```

## Environment Variables

See `.env.example` for required environment variables including:
- Database connection
- Redis connection
- AI service API keys (Gemini, OpenAI)
- Pinecone configuration
- Security settings