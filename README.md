# Bitewise Backend

FastAPI backend for the Bitewise application.

## Features

- FastAPI-based REST API
- SQLAlchemy ORM with migration support via Alembic
- Pydantic for data validation
- Testing with pytest
- Code quality with pre-commit hooks (black, isort, flake8, mypy)
- CI/CD with GitHub Actions

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aaniksahaa/bitewise-backend.git
   cd bitewise-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

5. Create a `.env` file in the root directory:
   ```
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///./bitewise.db
   ```

### Database Setup

Initialize the database with Alembic:

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Running the Application

```bash
python run.py
```

The API will be available at http://localhost:8000

API documentation will be available at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Testing

```bash
pytest
```

## Project Structure

```
bitewise-backend/
├── alembic.ini                # Alembic configuration
├── app/                       # Application package
│   ├── api/                   # API endpoints
│   │   ├── endpoints/         # API endpoint modules
│   │   └── router.py          # Main API router
│   ├── core/                  # Core functionality
│   │   └── config.py          # Settings and configuration
│   ├── db/                    # Database
│   │   └── session.py         # Database connection
│   ├── models/                # SQLAlchemy models
│   │   └── base.py            # Base model class
│   ├── schemas/               # Pydantic schemas
│   │   └── base.py            # Base schemas
│   ├── services/              # Business logic
│   └── main.py                # FastAPI application
├── migrations/                # Alembic migrations
├── tests/                     # Test suite
│   ├── conftest.py            # pytest fixtures
│   └── test_*.py              # Test modules
├── .env                       # Environment variables (not in git)
├── .pre-commit-config.yaml    # pre-commit configuration
├── .github/                   # GitHub configuration
│   └── workflows/             # GitHub Actions
│       └── ci.yml             # CI workflow
├── setup.cfg                  # Linter configuration
├── requirements.txt           # Dependencies
└── run.py                     # Application runner
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests with `pytest`
4. Make sure all linting checks pass
5. Submit a pull request

## License

[MIT License](LICENSE)
