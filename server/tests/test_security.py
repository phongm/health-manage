from app.core.security import create_access_token, parse_access_token
from app.core.exceptions import AuthError
import pytest


def test_jwt_roundtrip():
    token = create_access_token(42)
    assert parse_access_token(token) == 42


def test_jwt_invalid():
    with pytest.raises(AuthError):
        parse_access_token("not-a-token")
