import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def generate_test_jwt(user_id=1, email="testuser@example.com"):
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token
