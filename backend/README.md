# LifePilot Backend

FastAPI backend for the LifePilot life management platform.

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Database**: PostgreSQL 15
- **Cache**: Redis
- **Task Queue**: Celery

## Project Structure

```
backend/
├── alembic/              # Database migrations
│   ├── versions/         # Migration files
│   └── env.py           # Alembic environment config
├── app/
│   ├── core/            # Core configuration and utilities
│   │   ├── config.py    # Pydantic settings management
│   │   ├── database.py  # SQLAlchemy async setup
│   │   └── exceptions.py # Custom exceptions
│   ├── middleware/      # FastAPI middleware
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Data access layer
│   ├── routers/         # API endpoints
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── main.py          # Application entry point
├── tests/               # Test files
├── alembic.ini          # Alembic configuration
├── pyproject.toml       # Project dependencies
└── .env.example         # Environment template
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Copy environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Start PostgreSQL and Redis (using Docker):
   ```bash
   docker run -d --name lifepilot-db -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lifepilot postgres:15
   docker run -d --name lifepilot-redis -p 6379:6379 redis:7
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

When running in development mode (`DEBUG=true`), API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=html
```
