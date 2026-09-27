import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.auth.jwt_auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    get_optional_user,
    get_password_hash,
    verify_password,
)
from app.models.db_models import User

pytestmark = pytest.mark.security


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _unsigned_token(payload: dict) -> str:
    def segment(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{segment({'alg': 'none', 'typ': 'JWT'})}.{segment(payload)}."


def _future_exp() -> int:
    return int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())


def test_password_hash_roundtrip(test_password):
    hashed = get_password_hash(test_password)
    assert hashed != test_password
    assert hashed.startswith("$2")
    assert verify_password(test_password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = get_password_hash("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_returns_false_for_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_password_hashes_are_salted_per_call():
    assert get_password_hash("same-password") != get_password_hash("same-password")


def test_password_is_truncated_to_72_bytes():
    hashed = get_password_hash("a" * 80)
    assert verify_password("a" * 72 + "b" * 8, hashed) is True


def test_signing_secret_is_present_and_long_enough():
    assert SECRET_KEY
    assert len(SECRET_KEY) >= 16


def test_create_access_token_embeds_subject_role_and_expiry(test_user):
    token = create_access_token({"sub": test_user.id, "role": test_user.role})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == test_user.id
    assert payload["role"] == test_user.role
    assert payload["exp"] > int(datetime.now(UTC).timestamp())


def test_create_access_token_honours_custom_expiry(test_user):
    token = create_access_token({"sub": test_user.id}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["exp"] == pytest.approx(_future_exp(), abs=10)


def test_create_access_token_does_not_mutate_caller_payload(test_user):
    data = {"sub": test_user.id}
    create_access_token(data)
    assert data == {"sub": test_user.id}


def test_get_current_user_returns_matching_user(test_user, db_session):
    token = create_access_token({"sub": test_user.id})
    assert get_current_user(_credentials(token), db_session).id == test_user.id


@pytest.mark.parametrize("token_value", ["", "   ", "not-a-jwt", "a.b.c", "...."])
def test_get_current_user_rejects_malformed_token(token_value, db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token_value), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_sets_www_authenticate_header(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials("bogus"), db_session)
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}
    assert exc.value.detail == "Could not validate credentials"


def test_get_current_user_rejects_expired_token(test_user, db_session):
    token = create_access_token({"sub": test_user.id}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_rejects_token_signed_with_another_secret(test_user, db_session):
    token = jwt.encode(
        {"sub": test_user.id, "exp": _future_exp()},
        "attacker-controlled-secret",
        algorithm=ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_rejects_unsigned_alg_none_forgery(test_user, db_session):
    token = _unsigned_token({"sub": test_user.id, "exp": _future_exp()})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_requires_subject_claim(db_session):
    token = create_access_token({"role": "researcher"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_rejects_unknown_subject(db_session):
    token = create_access_token({"sub": "subject-does-not-exist"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_rejects_inactive_user(test_user, db_session):
    db_session.query(User).filter(User.id == test_user.id).update({"is_active": False})
    db_session.commit()
    token = create_access_token({"sub": test_user.id})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_credentials(token), db_session)
    assert exc.value.status_code == 400
    assert "Inactive" in exc.value.detail


def test_get_optional_user_returns_none_without_credentials(db_session):
    assert get_optional_user(None, db_session) is None


def test_get_optional_user_returns_none_for_invalid_token(db_session):
    assert get_optional_user(_credentials("bogus"), db_session) is None


def test_get_optional_user_returns_none_for_inactive_user(test_user, db_session):
    db_session.query(User).filter(User.id == test_user.id).update({"is_active": False})
    db_session.commit()
    token = create_access_token({"sub": test_user.id})
    assert get_optional_user(_credentials(token), db_session) is None


def test_get_optional_user_returns_user_for_valid_token(test_user, db_session):
    token = create_access_token({"sub": test_user.id})
    user = get_optional_user(_credentials(token), db_session)
    assert user is not None
    assert user.id == test_user.id


def test_role_claim_in_token_does_not_grant_privilege(test_user, db_session):
    token = create_access_token({"sub": test_user.id, "role": "admin"})
    user = get_current_user(_credentials(token), db_session)
    assert user.role == "researcher"
