# Bitewise Backend

FastAPI backend for the Bitewise application.

## Features

- FastAPI-based REST API
- SQLAlchemy ORM with migration support via Alembic
- Pydantic for data validation
- Testing with pytest
- Code quality with pre-commit hooks (black, isort, flake8, mypy)
- CI/CD with GitHub Actions
- Authentication system with:
  - Email/Password Authentication with OTP verification
  - Google Social Login integration
  - Token-based API Authentication
  - Password reset functionality

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
   # Application
   SECRET_KEY=your_secret_key_here
   
   # Database
   DATABASE_URL=sqlite:///./bitewise.db
   
   # Email (Resend)
   RESEND_API_KEY=your_resend_api_key
   EMAIL_FROM=noreply@bitewise.io
   EMAIL_FROM_NAME=BiteWise
   
   # Google OAuth
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_CALLBACK_URL=http://localhost:8000/api/v1/auth/google/callback
   ```

### Database Setup

Initialize the database with Alembic:

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

For a fresh setup, you can also use the migration script included:

```bash
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

## Authentication System

The Bitewise API provides a comprehensive authentication system with the following features:

### Email/Password Authentication

- User registration with email verification
- Two-factor authentication with email OTP for login
- Password reset functionality

### Google Social Login

- Integration with Google OAuth2
- Automatic account creation for new users
- Account linking for existing users

### Token-based Authentication

- JWT-based access tokens for API authentication
- Refresh tokens for obtaining new access tokens
- Token revocation (logout)

### Authentication Endpoints

All authentication endpoints are available under `/api/v1/auth/`. For detailed API documentation, please refer to the Swagger UI or ReDoc.

- **Register**: `POST /api/v1/auth/register`
- **Verify Email**: `POST /api/v1/auth/verify-email`
- **Login**: `POST /api/v1/auth/login`
- **Verify Login**: `POST /api/v1/auth/verify-login`
- **Google Login**: `GET /api/v1/auth/google/login`
- **Google Callback**: `GET /api/v1/auth/google/callback`
- **Refresh Token**: `POST /api/v1/auth/refresh`
- **Logout**: `POST /api/v1/auth/logout`
- **Reset Password Request**: `POST /api/v1/auth/reset-password/request`
- **Reset Password Complete**: `POST /api/v1/auth/reset-password/complete`

## Project Structure

```
bitewise-backend/
├── alembic.ini                # Alembic configuration
├── app/                       # Application package
│   ├── api/                   # API endpoints
│   │   ├── endpoints/         # API endpoint modules
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   └── health.py      # Health check endpoint
│   │   └── router.py          # Main API router
│   ├── core/                  # Core functionality
│   │   └── config.py          # Settings and configuration
│   ├── db/                    # Database
│   │   └── session.py         # Database connection
│   ├── models/                # SQLAlchemy models
│   │   ├── auth.py            # Authentication models
│   │   ├── user.py            # User model
│   │   └── base.py            # Base model class
│   ├── schemas/               # Pydantic schemas
│   │   ├── auth.py            # Authentication schemas
│   │   └── base.py            # Base schemas
│   ├── services/              # Business logic
│   │   ├── auth.py            # Authentication service
│   │   └── email.py           # Email service
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
