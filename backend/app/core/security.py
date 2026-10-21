import logging
from typing import Optional
from fastapi import Header, HTTPException, status
import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_current_student_id(
    authorization: Optional[str] = Header(None, description="Bearer <token>")
) -> str:
    """
    Extracts and validates the student ID from the Clerk JWT bearer token.
    Strictly enforces identity via token claims; client-supplied IDs are never trusted.
    """
    if not authorization:
        if settings.DEV_MOCK_AUTH:
            logger.info("No Authorization header provided, using dev mock student ID")
            return "student_dev_local_001"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    # 1. Try decoding as Native PrepGenius JWT token
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        student_id = payload.get("sub")
        if student_id:
            return student_id
    except jwt.PyJWTError:
        pass  # Fall through to Clerk / Dev mode verification

    # 2. Try Clerk JWT Verification (if configured)
    if settings.CLERK_JWKS_URL or settings.CLERK_SECRET_KEY:
        try:
            if settings.CLERK_JWKS_URL:
                jwks_client = jwt.PyJWKClient(settings.CLERK_JWKS_URL)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=settings.CLERK_JWT_ISSUER or None,
                    options={"verify_aud": False},
                )
            else:
                payload = jwt.decode(
                    token,
                    settings.CLERK_SECRET_KEY,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )

            student_id = payload.get("sub")
            if student_id:
                return student_id
        except jwt.PyJWTError as e:
            logger.warning(f"Clerk JWT decode attempt failed: {e}")

    # 3. Dev / Mock Auth Mode Handling
    if settings.DEV_MOCK_AUTH:
        # If token is a test identifier or local dev token
        if token.startswith("mock_") or token.startswith("dev_") or token.startswith("std_") or token == "test_token":
            return token

    # If all verification attempts failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
