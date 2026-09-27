import pytest
from jose import jwt

from app.auth.jwt_auth import ALGORITHM, SECRET_KEY, verify_password
from app.models.db_models import User

pytestmark = pytest.mark.security

PASSWORD = "S3cure-Passw0rd!"


def _signup_payload(email: str, **overrides) -> dict:
    payload = {
        "name": "Asha Researcher",
        "email": email,
        "password": PASSWORD,
        "institution": "BHU",
    }
    payload.update(overrides)
    return payload


def test_signup_returns_token_and_user_payload(api_client):
    response = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("signup-ok@example.test")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "signup-ok@example.test"
    assert body["user"]["role"] == "researcher"
    assert body["access_token"]


def test_signup_token_identifies_the_new_user(api_client):
    body = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("signup-sub@example.test")
    ).json()
    payload = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == body["user"]["id"]


def test_signup_defaults_role_to_researcher(api_client):
    body = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("signup-role@example.test")
    ).json()
    assert body["user"]["role"] == "researcher"


def test_signup_never_stores_plaintext_password(api_client, db_session):
    api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("signup-hash@example.test")
    ).json()
    user = db_session.query(User).filter(User.email == "signup-hash@example.test").first()
    assert user is not None
    assert user.hashed_password != PASSWORD
    assert PASSWORD not in user.hashed_password
    assert verify_password(PASSWORD, user.hashed_password) is True


def test_signup_rejects_duplicate_email(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("dupe@example.test"))
    response = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("dupe@example.test")
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_signup_validates_request_shape(api_client):
    response = api_client.post("/api/v1/auth/signup", json={"email": "no-name@example.test"})
    assert response.status_code == 422


def test_login_returns_token_for_valid_credentials(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("login-ok@example.test"))
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "login-ok@example.test", "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login-ok@example.test"


def test_login_token_opens_the_profile_route(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("roundtrip@example.test"))
    token = api_client.post(
        "/api/v1/auth/login",
        json={"email": "roundtrip@example.test", "password": PASSWORD},
    ).json()["access_token"]
    response = api_client.get(
        "/api/v1/auth/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "roundtrip@example.test"


def test_login_rejects_wrong_password(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("wrongpw@example.test"))
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.test", "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_rejects_unknown_email(api_client):
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.test", "password": PASSWORD},
    )
    assert response.status_code == 401


def test_login_error_does_not_reveal_whether_email_exists(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("known@example.test"))
    unknown = api_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.test", "password": PASSWORD},
    )
    known = api_client.post(
        "/api/v1/auth/login",
        json={"email": "known@example.test", "password": "wrong-password"},
    )
    assert unknown.status_code == known.status_code
    assert unknown.json()["detail"] == known.json()["detail"]


@pytest.mark.xfail(
    reason="login never checks user.is_active, so a deactivated account can still mint a token",
    strict=False,
)
def test_login_rejects_inactive_user(api_client, db_session):
    body = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("inactive@example.test")
    ).json()
    db_session.query(User).filter(User.id == body["user"]["id"]).update(
        {"is_active": False}
    )
    db_session.commit()
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.test", "password": PASSWORD},
    )
    assert response.status_code == 401


def test_profile_rejects_missing_authorization_header(api_client):
    response = api_client.get("/api/v1/auth/profile")
    assert response.status_code == 401


def test_profile_rejects_malformed_authorization_header(api_client):
    response = api_client.get(
        "/api/v1/auth/profile", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_profile_rejects_token_for_unknown_subject(api_client):
    from app.auth.jwt_auth import create_access_token

    token = create_access_token({"sub": "deleted-user-id"})
    response = api_client.get(
        "/api/v1/auth/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_profile_returns_current_user_fields(authenticated_client, test_user):
    response = authenticated_client.get("/api/v1/auth/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == test_user.id
    assert body["email"] == test_user.email
    assert body["is_active"] is True
    assert "created_at" in body


def test_profile_never_returns_the_password_hash(authenticated_client):
    body = authenticated_client.get("/api/v1/auth/profile").json()
    assert "hashed_password" not in body
    assert "password" not in body


def test_forgot_password_accepts_known_email(api_client):
    api_client.post("/api/v1/auth/signup", json=_signup_payload("forgot@example.test"))
    response = api_client.post(
        "/api/v1/auth/forgot-password", json={"email": "forgot@example.test"}
    )
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.xfail(
    reason="forgot-password returns 404 for unknown emails, which enumerates registered accounts",
    strict=False,
)
def test_forgot_password_does_not_reveal_account_existence(api_client):
    response = api_client.post(
        "/api/v1/auth/forgot-password", json={"email": "never-registered@example.test"}
    )
    assert response.status_code == 200


@pytest.mark.xfail(
    reason="SignupRequest accepts a client-supplied role, so a caller can self-assign admin",
    strict=False,
)
def test_signup_cannot_self_assign_admin_role(api_client):
    body = api_client.post(
        "/api/v1/auth/signup", json=_signup_payload("escalate@example.test", role="admin")
    ).json()
    assert body["user"]["role"] != "admin"
