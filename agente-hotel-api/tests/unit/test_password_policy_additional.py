import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.security.password_policy import PasswordPolicy, PasswordPolicyViolation


class DummyResult:
    def __init__(self, hashes):
        self._hashes = hashes

    def scalars(self):
        return SimpleNamespace(all=lambda: self._hashes)


class DummySession:
    def __init__(self, hashes=None, raise_exc=False):
        self._hashes = hashes or []
        self.raise_exc = raise_exc

    async def execute(self, stmt):  # stmt ignored for dummy
        if self.raise_exc:
            raise RuntimeError("db fail")
        return DummyResult(self._hashes)


@pytest.mark.asyncio
async def test_password_strength_all_violations():
    policy = PasswordPolicy(min_length=12)
    ok, violations = policy.validate_password_strength("abc")  # too short, lacks complexity
    assert not ok
    # Should list multiple violation messages
    assert any("at least" in v.lower() for v in violations)


@pytest.mark.asyncio
async def test_password_strength_valid():
    policy = PasswordPolicy(min_length=12)
    pw = "StrongPass123!"  # meets all criteria
    ok, violations = policy.validate_password_strength(pw)
    assert ok
    assert violations == []


@pytest.mark.asyncio
async def test_password_history_reuse_detected():
    policy = PasswordPolicy(history_size=5)
    # Prepare a previously used hash for same password
    from app.security.password_policy import pwd_context
    reused_hash = pwd_context.hash("StrongPass123!")
    session = DummySession(hashes=[reused_hash])
    valid, error = await policy.validate_password_history(session, user_id="u1", new_password="StrongPass123!")
    assert not valid
    assert "recently" in error.lower()


@pytest.mark.asyncio
async def test_password_history_fail_open_on_error():
    policy = PasswordPolicy(history_size=5)
    session = DummySession(raise_exc=True)
    valid, error = await policy.validate_password_history(session, user_id="u2", new_password="AnotherStrong1!")
    assert valid  # fail open
    assert error is None


@pytest.mark.asyncio
async def test_rotation_required_when_none_last_changed():
    policy = PasswordPolicy(rotation_days=90)
    assert policy.check_rotation_required(None) is True


@pytest.mark.asyncio
async def test_rotation_required_due_to_age():
    policy = PasswordPolicy(rotation_days=30)
    old = datetime.now(timezone.utc) - timedelta(days=45)
    assert policy.check_rotation_required(old) is True


@pytest.mark.asyncio
async def test_rotation_not_required_recent():
    policy = PasswordPolicy(rotation_days=30)
    recent = datetime.now(timezone.utc) - timedelta(days=10)
    assert policy.check_rotation_required(recent) is False


@pytest.mark.asyncio
async def test_complete_validation_raises_on_violations():
    policy = PasswordPolicy(min_length=12)
    bad_pw = "short"  # strength fail
    session = DummySession(hashes=[])  # history passes
    with pytest.raises(PasswordPolicyViolation) as exc:
        await policy.validate_password_complete(
            password=bad_pw,
            session=session,
            user_id="u1",
            last_changed=datetime.now(timezone.utc) - timedelta(days=120),
            skip_history=False,
        )
    assert "does not" in str(exc.value).lower()
    assert exc.value.violations


@pytest.mark.asyncio
async def test_complete_validation_success_skip_history():
    policy = PasswordPolicy(min_length=12)
    good = "StrongPass123!"
    session = DummySession(hashes=[])  # would pass history anyway
    # skip_history True for new user
    await policy.validate_password_complete(
        password=good,
        session=session,
        user_id="new-user",
        last_changed=None,
        skip_history=True,
    )


@pytest.mark.asyncio
async def test_hash_and_verify_password_roundtrip():
    policy = PasswordPolicy()
    raw = "StrongPass123!"
    hashed = policy.hash_password(raw)
    assert hashed != raw
    assert policy.verify_password(raw, hashed) is True
    assert policy.verify_password("Wrong123!", hashed) is False
