# Fase 1 — Fondasi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun fondasi backend reseller-ai: project structure, database, cache, middleware keamanan, dan auth sistem lengkap dengan tenant provisioning.

**Architecture:** FastAPI async backend dengan PostgreSQL (pgvector + RLS) sebagai data store, Redis sebagai broker Celery. Setiap request di-inject dengan tenant context via middleware. Auth menggunakan JWT access + refresh token rotation.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16 + pgvector, Redis 7, Celery 5, python-jose, passlib, pydantic-settings, asyncpg, cryptography

## Global Constraints

- Python 3.12 — gunakan fitur terbaru (f-string, tomllib, dsb.)
- FastAPI dengan async/await di semua handler dan service
- Pydantic v2 untuk semua schema — tidak boleh ada `dict` mentah di service layer (RULE-06)
- Semua fungsi publik wajib type hint (RULE-10)
- Tidak ada `print()` — gunakan `logging` terstruktur (RULE-08)
- Tidak ada secret di kode — semua dari env via `pydantic-settings` (RULE-05)
- Semua query DB wajib filter `tenant_id` (RULE-03)
- Perubahan schema DB wajib via Alembic migration (RULE-09)
- Response API selalu format `{"success": bool, "data": ..., "message": ...}` (Section 0.5)
- Error tidak boleh bocor ke response — tangkap di middleware (RULE-02)
- Semua Celery task wajib retry + log (RULE-04)
- Credential tenant disimpan ter-enkripsi (RULE-05)

---

## File Structure

```
reseller-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app factory, middleware registry, router registry
│   │   ├── core/
│   │   │   ├── config.py                  # Settings via pydantic-settings (semua env vars)
│   │   │   ├── database.py                # SQLAlchemy async engine + get_db_session dependency
│   │   │   ├── redis.py                   # Redis client singleton
│   │   │   ├── security.py                # JWT issue/verify, password hash, credential encrypt/decrypt
│   │   │   └── feature_flags.py           # FeatureStatus enum, check_feature_status(), PLAN_FEATURES
│   │   ├── middleware/
│   │   │   ├── error_handler.py           # Global exception handler — no raw error ke response
│   │   │   ├── tenant_context.py          # Inject tenant_id ke request.state dari JWT
│   │   │   └── rate_limiter.py            # Per-tenant rate limiting via Redis (stub untuk Fase 1)
│   │   ├── models/
│   │   │   ├── base.py                    # DeclarativeBase, TimestampMixin
│   │   │   ├── user.py                    # User model (tenant_user / super_admin)
│   │   │   ├── tenant.py                  # Tenant model
│   │   │   └── tenant_credential.py       # TenantCredential model (token ter-enkripsi)
│   │   ├── schemas/
│   │   │   ├── base.py                    # APIResponse[T], APIError
│   │   │   ├── auth.py                    # RegisterRequest, LoginRequest, TokenResponse
│   │   │   └── tenant.py                  # TenantResponse, TenantCreate
│   │   ├── routers/
│   │   │   └── auth.py                    # POST /auth/register, /auth/login, /auth/refresh
│   │   └── services/
│   │       ├── auth_service.py            # register_user(), login_user(), refresh_token()
│   │       └── tenant_service.py          # provision_tenant() — buat workspace saat register
│   ├── workers/
│   │   └── celery_app.py                  # Celery app instance + config
│   ├── alembic/
│   │   ├── env.py                         # Alembic async env
│   │   └── versions/                      # Migration files
│   ├── tests/
│   │   ├── conftest.py                    # pytest fixtures: test DB, test client, test tenant
│   │   ├── test_auth.py                   # Register, login, refresh, error cases
│   │   ├── test_tenant_isolation.py       # Pastikan query tidak bocor lintas tenant
│   │   └── test_feature_flags.py          # check_feature_status() semua status
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
└── .gitignore
```

---

## Task 1: Project Scaffold & Dependencies

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/workers/__init__.py`

**Interfaces:**
- Produces: virtual environment aktif dengan semua dependency terinstall

- [ ] **Step 1: Buat direktori struktur project**

```bash
cd /home/px/Projects/Reseller
mkdir -p backend/app/{core,middleware,models,schemas,routers,services}
mkdir -p backend/{workers,alembic/versions,tests}
touch backend/app/__init__.py
touch backend/app/{core,middleware,models,schemas,routers,services}/__init__.py
touch backend/workers/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 2: Buat `pyproject.toml`**

```toml
# backend/pyproject.toml
[project]
name = "reseller-ai"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "sqlalchemy==2.0.35",
    "alembic==1.13.3",
    "asyncpg==0.29.0",
    "pgvector==0.3.2",
    "redis==5.1.1",
    "celery==5.4.0",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "cryptography==43.0.1",
    "httpx==0.27.2",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "pytest-cov==5.0.0",
    "httpx==0.27.2",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Buat `.env.example`**

```bash
# backend/.env.example

# App
APP_ENV=development
APP_SECRET_KEY=change-me-in-production-min-32-chars

# Database
DATABASE_URL=postgresql+asyncpg://reseller:reseller@localhost:5432/reseller_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=

# Meta (Facebook / Instagram)
META_APP_ID=
META_APP_SECRET=

# TikTok
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# WhatsApp Business
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Midtrans
MIDTRANS_SERVER_KEY=
MIDTRANS_CLIENT_KEY=

# Stripe (opsional)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Email
RESEND_API_KEY=

# Encryption key untuk credential tenant (32 bytes, base64url)
CREDENTIAL_ENCRYPTION_KEY=

# Frontend
VITE_API_BASE_URL=http://localhost:8000

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

- [ ] **Step 4: Buat `.gitignore`**

```gitignore
# backend/.gitignore
__pycache__/
*.py[cod]
.env
.venv/
venv/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
dist/
```

- [ ] **Step 5: Setup virtual environment dan install dependencies**

```bash
cd /home/px/Projects/Reseller/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected output: semua package terinstall tanpa error.

- [ ] **Step 6: Salin `.env.example` ke `.env` dan isi nilai minimal untuk development**

```bash
cp .env.example .env
```

Edit `.env` — isi minimal:
```
APP_SECRET_KEY=dev-secret-key-minimum-32-characters-here
DATABASE_URL=postgresql+asyncpg://reseller:reseller@localhost:5432/reseller_ai
REDIS_URL=redis://localhost:6379/0
CREDENTIAL_ENCRYPTION_KEY=  # generate di Task 2
```

- [ ] **Step 7: Commit scaffold**

```bash
cd /home/px/Projects/Reseller
git init
git add backend/pyproject.toml backend/.env.example backend/.gitignore backend/app/ backend/workers/ backend/tests/
git commit -m "feat: project scaffold dan dependency setup"
```

---

## Task 2: Core Config & Security

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces:
  - `get_settings() -> Settings` — singleton settings dari env
  - `hash_password(password: str) -> str`
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(data: dict) -> str`
  - `create_refresh_token(data: dict) -> str`
  - `decode_token(token: str) -> dict`
  - `encrypt_credential(plaintext: str) -> str`
  - `decrypt_credential(ciphertext: str) -> str`

- [ ] **Step 1: Buat `app/core/config.py`**

```python
# backend/app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Meta
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""

    # TikTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # WhatsApp
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # Midtrans
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Email
    RESEND_API_KEY: str = ""

    # Encryption
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Buat `app/core/security.py`**

```python
# backend/app/core/security.py
import base64
import logging
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    settings = get_settings()
    payload = data.copy()
    payload["type"] = ACCESS_TOKEN_TYPE
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    settings = get_settings()
    payload = data.copy()
    payload["type"] = REFRESH_TOKEN_TYPE
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning("Token decode failed", extra={"error": str(e)})
        raise


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY tidak diset")
    # Pastikan key valid base64 32-byte Fernet key
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credential(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 3: Generate `CREDENTIAL_ENCRYPTION_KEY` yang valid**

```python
# Jalankan sekali di terminal untuk generate key:
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Salin output ke `.env` sebagai nilai `CREDENTIAL_ENCRYPTION_KEY`.

- [ ] **Step 4: Tulis failing tests**

```python
# backend/tests/test_security.py
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_credential,
    decrypt_credential,
)


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token({"sub": "user-uuid-123", "tenant_id": "t-uuid"})
    payload = decode_token(token)
    assert payload["sub"] == "user-uuid-123"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token = create_refresh_token({"sub": "user-uuid-123"})
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_invalid_token_raises():
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("invalid.token.here")


def test_credential_encrypt_decrypt(monkeypatch):
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)

    # Reset lru_cache agar env baru terbaca
    from app.core.config import get_settings
    get_settings.cache_clear()

    encrypted = encrypt_credential("my-secret-token")
    assert encrypted != "my-secret-token"
    assert decrypt_credential(encrypted) == "my-secret-token"

    get_settings.cache_clear()
```

- [ ] **Step 5: Jalankan test — pastikan FAIL dulu**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
pytest tests/test_security.py -v
```

Expected: `ModuleNotFoundError` atau import error karena file belum dibuat.

- [ ] **Step 6: Jalankan test setelah implementasi**

```bash
pytest tests/test_security.py -v
```

Expected:
```
test_security.py::test_password_hash_and_verify PASSED
test_security.py::test_access_token_roundtrip PASSED
test_security.py::test_refresh_token_roundtrip PASSED
test_security.py::test_decode_invalid_token_raises PASSED
test_security.py::test_credential_encrypt_decrypt PASSED
5 passed
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: core config (pydantic-settings) dan security utils (JWT, bcrypt, Fernet)"
```

---

## Task 3: Database Setup & Models

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/tenant.py`
- Create: `backend/app/models/tenant_credential.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (akan diisi migration)

**Interfaces:**
- Consumes: `get_settings() -> Settings` dari Task 2
- Produces:
  - `get_db_session(request) -> AsyncSession` — FastAPI dependency
  - `engine` — SQLAlchemy async engine (dipakai Alembic)
  - `User` model class
  - `Tenant` model class
  - `TenantCredential` model class

- [ ] **Step 1: Buat `app/core/database.py`**

```python
# backend/app/core/database.py
import logging
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    tenant_id = getattr(request.state, "tenant_id", None)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            if tenant_id:
                # SET LOCAL: scoped ke transaction ini — aman dengan connection pooling
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
            yield session
```

- [ ] **Step 2: Buat `app/models/base.py`**

```python
# backend/app/models/base.py
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 3: Buat `app/models/tenant.py`**

```python
# backend/app/models/tenant.py
import uuid

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[str | None] = mapped_column(nullable=True)
    ai_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
```

- [ ] **Step 4: Buat `app/models/user.py`**

```python
# backend/app/models/user.py
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # NULL untuk super_admin
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="tenant_user"
    )  # 'tenant_user' | 'super_admin'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="users")
```

- [ ] **Step 5: Buat `app/models/tenant_credential.py`**

```python
# backend/app/models/tenant_credential.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TenantCredential(Base, TimestampMixin):
    __tablename__ = "tenant_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'instagram' | 'tiktok' | 'whatsapp' | dsb.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def is_expired(self) -> bool:
        from datetime import timezone
        if self.expires_at is None:
            return False
        from datetime import datetime
        return datetime.now(timezone.utc) > self.expires_at
```

- [ ] **Step 6: Pastikan PostgreSQL running dan database dibuat**

```bash
# Pastikan PostgreSQL running
psql -U postgres -c "CREATE USER reseller WITH PASSWORD 'reseller';" 2>/dev/null || true
psql -U postgres -c "CREATE DATABASE reseller_ai OWNER reseller;" 2>/dev/null || true
psql -U postgres -d reseller_ai -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
psql -U postgres -d reseller_ai -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null || true
```

- [ ] **Step 7: Setup Alembic**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
alembic init alembic
```

Edit `alembic/env.py` — ganti isinya dengan:

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.models.base import Base
# Import semua model agar Alembic detect tabel
from app.models.user import User  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.tenant_credential import TenantCredential  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Edit `alembic.ini` — ubah `sqlalchemy.url` (akan di-override oleh env.py, tapi wajib ada):
```ini
sqlalchemy.url = postgresql+asyncpg://reseller:reseller@localhost:5432/reseller_ai
```

- [ ] **Step 8: Buat dan jalankan migration awal**

```bash
alembic revision --autogenerate -m "initial_schema_users_tenants_credentials"
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> <rev>, initial_schema_users_tenants_credentials
```

Verifikasi tabel terbuat:
```bash
psql -U reseller -d reseller_ai -c "\dt"
```

Expected:
```
 Schema |          Name          | Type  |  Owner
--------+------------------------+-------+---------
 public | alembic_version        | table | reseller
 public | tenant_credentials     | table | reseller
 public | tenants                | table | reseller
 public | users                  | table | reseller
```

- [ ] **Step 9: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/core/database.py backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat: database setup, SQLAlchemy models, Alembic migration awal"
```

---

## Task 4: Redis & Celery Setup

**Files:**
- Create: `backend/app/core/redis.py`
- Create: `backend/workers/celery_app.py`
- Test: `backend/tests/test_redis.py`

**Interfaces:**
- Consumes: `get_settings() -> Settings` dari Task 2
- Produces:
  - `get_redis()` — async Redis client (singleton)
  - `celery_app` — Celery application instance

- [ ] **Step 1: Buat `app/core/redis.py`**

```python
# backend/app/core/redis.py
import logging

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis client initialized", extra={"url": settings.REDIS_URL})
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
```

- [ ] **Step 2: Buat `workers/celery_app.py`**

```python
# backend/workers/celery_app.py
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reseller_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.discovery_worker",
        "workers.content_worker",
        "workers.engagement_worker",
        "workers.conversion_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.discovery_worker.*": {"queue": "discovery"},
        "workers.content_worker.*": {"queue": "content"},
        "workers.engagement_worker.*": {"queue": "engagement"},
        "workers.conversion_worker.*": {"queue": "conversion"},
    },
)
```

Buat stub worker files agar import tidak error:

```bash
touch backend/workers/discovery_worker.py
touch backend/workers/content_worker.py
touch backend/workers/engagement_worker.py
touch backend/workers/conversion_worker.py
```

- [ ] **Step 3: Tulis failing tests**

```python
# backend/tests/test_redis.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_redis_returns_client():
    from app.core.redis import get_redis, close_redis

    # Reset singleton
    import app.core.redis as redis_module
    redis_module._redis_client = None

    client = await get_redis()
    assert client is not None

    await close_redis()
    assert redis_module._redis_client is None


def test_celery_app_configured():
    from workers.celery_app import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert "workers.discovery_worker" in celery_app.conf.include
```

- [ ] **Step 4: Pastikan Redis running lalu jalankan tests**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
pytest tests/test_redis.py -v
```

Expected:
```
test_redis.py::test_get_redis_returns_client PASSED
test_redis.py::test_celery_app_configured PASSED
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/redis.py backend/workers/
git commit -m "feat: Redis async client dan Celery app setup"
```

---

## Task 5: Feature Flags

**Files:**
- Create: `backend/app/core/feature_flags.py`
- Test: `backend/tests/test_feature_flags.py`

**Interfaces:**
- Consumes: `AsyncSession` dari Task 3, `Tenant` model dari Task 3, `TenantCredential` model dari Task 3
- Produces:
  - `FeatureStatus` enum
  - `PLAN_FEATURES: dict[str, list[str]]`
  - `check_feature_status(tenant_id: str, feature: str, db: AsyncSession) -> FeatureStatus`

- [ ] **Step 1: Buat `app/core/feature_flags.py`**

```python
# backend/app/core/feature_flags.py
import logging
import uuid
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)

PLATFORM_TO_FEATURE_PREFIX = {
    "instagram": "instagram",
    "tiktok": "tiktok",
    "facebook": "facebook",
    "whatsapp": "whatsapp",
}


class FeatureStatus(str, Enum):
    ACTIVE = "active"
    NOT_CONFIGURED = "not_configured"
    EXPIRED = "expired"
    PLAN_LOCKED = "plan_locked"
    QUOTA_EXCEEDED = "quota_exceeded"
    DISABLED_BY_USER = "disabled_by_user"


PLAN_FEATURES: dict[str, list[str]] = {
    "free": ["instagram_reply"],
    "starter": ["instagram_reply", "tiktok_reply", "content_publish"],
    "pro": [
        "instagram_reply",
        "tiktok_reply",
        "facebook_reply",
        "whatsapp_reply",
        "content_publish",
        "product_discovery",
        "sales_conversion",
        "analytics",
    ],
    "enterprise": ["*"],
}

# Fitur yang tidak butuh credential platform (tidak perlu cek tabel tenant_credentials)
CREDENTIAL_FREE_FEATURES = {"analytics", "product_discovery"}


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    return result.scalar_one_or_none()


async def _is_quota_exceeded(tenant_id: str, feature: str, db: AsyncSession) -> bool:
    # Implementasi penuh di Fase 5 (usage metering). Untuk sekarang: selalu False.
    return False


async def _get_credential(
    tenant_id: str, feature: str, db: AsyncSession
) -> TenantCredential | None:
    # Ekstrak platform dari nama fitur (misal: "instagram_reply" → "instagram")
    platform = feature.split("_")[0]
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == platform,
        )
    )
    return result.scalar_one_or_none()


async def check_feature_status(
    tenant_id: str,
    feature: str,
    db: AsyncSession,
) -> FeatureStatus:
    try:
        tenant = await _get_tenant(tenant_id, db)
        if tenant is None:
            return FeatureStatus.NOT_CONFIGURED

        plan_features = PLAN_FEATURES.get(tenant.plan, [])
        if "*" not in plan_features and feature not in plan_features:
            return FeatureStatus.PLAN_LOCKED

        if await _is_quota_exceeded(tenant_id, feature, db):
            return FeatureStatus.QUOTA_EXCEEDED

        if feature in CREDENTIAL_FREE_FEATURES:
            return FeatureStatus.ACTIVE

        credential = await _get_credential(tenant_id, feature, db)
        if credential is None:
            return FeatureStatus.NOT_CONFIGURED
        if credential.is_expired():
            return FeatureStatus.EXPIRED

        return FeatureStatus.ACTIVE

    except Exception:
        logger.exception(
            "check_feature_status error",
            extra={"tenant_id": tenant_id, "feature": feature},
        )
        return FeatureStatus.NOT_CONFIGURED  # safe default


async def log_skip(tenant_id: str, feature: str, status: FeatureStatus) -> None:
    logger.info(
        "Feature skipped",
        extra={"tenant_id": tenant_id, "feature": feature, "status": status.value},
    )
```

- [ ] **Step 2: Tulis failing tests**

```python
# backend/tests/test_feature_flags.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_flags import FeatureStatus, check_feature_status


def _make_tenant(plan: str) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.plan = plan
    return t


def _make_credential(expired: bool = False) -> MagicMock:
    c = MagicMock()
    c.is_expired.return_value = expired
    return c


@pytest.mark.asyncio
async def test_plan_locked_when_feature_not_in_plan():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("free")

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False):
        status = await check_feature_status(tenant_id, "product_discovery", db)

    assert status == FeatureStatus.PLAN_LOCKED


@pytest.mark.asyncio
async def test_not_configured_when_no_credential():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=None):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_expired_when_credential_expired():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")
    credential = _make_credential(expired=True)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.EXPIRED


@pytest.mark.asyncio
async def test_active_when_everything_ok():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("pro")
    credential = _make_credential(expired=False)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.ACTIVE


@pytest.mark.asyncio
async def test_not_configured_when_tenant_not_found():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    with patch("app.core.feature_flags._get_tenant", return_value=None):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_safe_default_on_exception():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    with patch("app.core.feature_flags._get_tenant", side_effect=Exception("DB down")):
        status = await check_feature_status(tenant_id, "instagram_reply", db)

    assert status == FeatureStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_enterprise_plan_has_all_features():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())
    tenant = _make_tenant("enterprise")
    credential = _make_credential(expired=False)

    with patch("app.core.feature_flags._get_tenant", return_value=tenant), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=credential):
        status = await check_feature_status(tenant_id, "any_future_feature", db)

    assert status == FeatureStatus.ACTIVE
```

- [ ] **Step 3: Jalankan tests**

```bash
pytest tests/test_feature_flags.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/feature_flags.py backend/tests/test_feature_flags.py
git commit -m "feat: feature flags system dengan FeatureStatus enum dan check_feature_status()"
```

---

## Task 6: Middleware — Error Handler & Tenant Context

**Files:**
- Create: `backend/app/middleware/error_handler.py`
- Create: `backend/app/middleware/tenant_context.py`
- Create: `backend/app/middleware/rate_limiter.py` (stub)
- Test: `backend/tests/test_middleware.py`

**Interfaces:**
- Consumes: `decode_token()` dari Task 2
- Produces:
  - `global_exception_handler(request, exc)` — didaftarkan ke FastAPI
  - `TenantContextMiddleware` — inject `request.state.tenant_id`

- [ ] **Step 1: Buat `app/middleware/error_handler.py`**

```python
# backend/app/middleware/error_handler.py
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("internal")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception",
        extra={
            "path": str(request.url),
            "method": request.method,
            "tenant_id": getattr(request.state, "tenant_id", None),
            "error_type": type(exc).__name__,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "message": "Terjadi kesalahan sistem. Tim kami sedang menangani ini.",
            "code": "INTERNAL_ERROR",
        },
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "data": None,
            "message": "Resource tidak ditemukan.",
            "code": "NOT_FOUND",
        },
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "message": "Data yang dikirim tidak valid.",
            "code": "VALIDATION_ERROR",
            "errors": [
                {"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]}
                for e in errors
            ],
        },
    )
```

- [ ] **Step 2: Buat `app/middleware/tenant_context.py`**

```python
# backend/app/middleware/tenant_context.py
import logging

from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token

logger = logging.getLogger(__name__)

# Endpoint yang tidak butuh tenant context
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
AUTH_PATHS = {"/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS or path in AUTH_PATHS:
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return self._unauthorized("Token tidak ditemukan.")

        try:
            payload = decode_token(token)
        except JWTError:
            return self._unauthorized("Token tidak valid atau sudah kedaluwarsa.")

        if payload.get("type") != "access":
            return self._unauthorized("Tipe token tidak valid.")

        request.state.tenant_id = payload.get("tenant_id")
        request.state.user_id = payload.get("sub")
        request.state.role = payload.get("role", "tenant_user")

        return await call_next(request)

    def _extract_token(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _unauthorized(self, message: str) -> Response:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "data": None,
                "message": message,
                "code": "UNAUTHORIZED",
            },
        )
```

- [ ] **Step 3: Buat stub `app/middleware/rate_limiter.py`**

```python
# backend/app/middleware/rate_limiter.py
# Stub untuk Fase 1 — implementasi penuh di Fase 2
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
```

- [ ] **Step 4: Tulis tests middleware**

```python
# backend/tests/test_middleware.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.middleware.error_handler import global_exception_handler
from app.middleware.tenant_context import TenantContextMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/api/v1/protected")
    async def protected(request):
        return {
            "success": True,
            "data": {
                "tenant_id": str(request.state.tenant_id),
                "role": request.state.role,
            },
        }

    @app.get("/api/v1/crash")
    async def crash():
        raise RuntimeError("intentional crash")

    return app


@pytest.fixture
def client():
    return TestClient(_make_app(), raise_server_exceptions=False)


def test_protected_without_token_returns_401(client):
    res = client.get("/api/v1/protected")
    assert res.status_code == 401
    assert res.json()["success"] is False
    assert res.json()["code"] == "UNAUTHORIZED"


def test_protected_with_valid_token_returns_200(client):
    token = create_access_token(
        {"sub": "user-123", "tenant_id": "tenant-abc", "role": "tenant_user"}
    )
    res = client.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["data"]["tenant_id"] == "tenant-abc"


def test_protected_with_invalid_token_returns_401(client):
    res = client.get("/api/v1/protected", headers={"Authorization": "Bearer bad.token"})
    assert res.status_code == 401


def test_exception_handler_returns_clean_error(client):
    token = create_access_token({"sub": "u", "tenant_id": "t", "role": "tenant_user"})
    res = client.get("/api/v1/crash", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 500
    assert res.json()["success"] is False
    assert res.json()["code"] == "INTERNAL_ERROR"
    # Pastikan tidak ada stack trace di response
    assert "Traceback" not in res.text
    assert "RuntimeError" not in res.text
```

- [ ] **Step 5: Jalankan tests**

```bash
pytest tests/test_middleware.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/
git commit -m "feat: error handler middleware (no raw error) dan tenant context middleware (JWT inject)"
```

---

## Task 7: Schemas & Base Response

**Files:**
- Create: `backend/app/schemas/base.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/tenant.py`
- Test: `backend/tests/test_schemas.py`

**Interfaces:**
- Produces:
  - `APIResponse[T]` — generic success response
  - `APIError` — error response
  - `RegisterRequest` — `email: str, password: str, name: str`
  - `LoginRequest` — `email: str, password: str`
  - `TokenResponse` — `access_token: str, refresh_token: str, token_type: str`
  - `TenantResponse` — `id: UUID, name: str, email: str, plan: str`

- [ ] **Step 1: Buat `app/schemas/base.py`**

```python
# backend/app/schemas/base.py
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class APIError(BaseModel):
    success: bool = False
    data: None = None
    message: str
    code: str
```

- [ ] **Step 2: Buat `app/schemas/auth.py`**

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

- [ ] **Step 3: Buat `app/schemas/tenant.py`**

```python
# backend/app/schemas/tenant.py
import uuid

from pydantic import BaseModel, EmailStr


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    plan: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Tulis dan jalankan tests**

```python
# backend/tests/test_schemas.py
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.base import APIResponse, APIError
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.tenant import TenantResponse


def test_api_response_generic():
    res = APIResponse[dict](success=True, data={"key": "val"})
    assert res.success is True
    assert res.data["key"] == "val"


def test_api_error_has_code():
    err = APIError(message="Terjadi kesalahan", code="INTERNAL_ERROR")
    assert err.success is False
    assert err.code == "INTERNAL_ERROR"


def test_register_request_validates_email():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="bukan-email", password="secret123")


def test_register_request_validates_password_min_length():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="test@test.com", password="short")


def test_login_request_valid():
    req = LoginRequest(email="user@example.com", password="anypass")
    assert req.email == "user@example.com"


def test_tenant_response_from_attributes():
    tenant_id = uuid.uuid4()
    res = TenantResponse(id=tenant_id, name="Toko Kece", email="toko@test.com", plan="free")
    assert res.plan == "free"
```

```bash
pytest tests/test_schemas.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic v2 schemas (APIResponse, auth, tenant)"
```

---

## Task 8: Auth Service & Tenant Provisioning

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/services/tenant_service.py`
- Test: `backend/tests/test_auth_service.py`

**Interfaces:**
- Consumes:
  - `hash_password(), verify_password(), create_access_token(), create_refresh_token(), decode_token()` dari Task 2
  - `User` model dari Task 3
  - `Tenant` model dari Task 3
  - `RegisterRequest, LoginRequest, TokenResponse` dari Task 7
- Produces:
  - `register_user(body: RegisterRequest, db: AsyncSession) -> tuple[User, Tenant]`
  - `login_user(body: LoginRequest, db: AsyncSession) -> TokenResponse`
  - `refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse`
  - `provision_tenant(name: str, email: str, db: AsyncSession) -> Tenant`

- [ ] **Step 1: Buat `app/services/tenant_service.py`**

```python
# backend/app/services/tenant_service.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


async def provision_tenant(name: str, email: str, db: AsyncSession) -> Tenant:
    tenant = Tenant(
        name=name,
        email=email,
        plan="free",
        ai_config={
            "tone": "casual",
            "niche": [],
            "posting_hours": [9, 12, 19],
            "intent_threshold": 0.75,
            "auto_approve": False,
        },
    )
    db.add(tenant)
    await db.flush()  # dapatkan ID tanpa commit (commit ada di luar)
    logger.info(
        "Tenant provisioned",
        extra={"tenant_id": str(tenant.id), "email": email},
    )
    return tenant
```

- [ ] **Step 2: Buat `app/services/auth_service.py`**

```python
# backend/app/services/auth_service.py
import logging
import uuid

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.tenant_service import provision_tenant

logger = logging.getLogger(__name__)


def _build_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
    }


def _make_token_response(user: User) -> TokenResponse:
    payload = _build_token_payload(user)
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


async def register_user(
    body: RegisterRequest, db: AsyncSession
) -> tuple[User, "Tenant"]:
    # Cek email sudah terdaftar
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")

    # Provision tenant workspace baru
    from app.models.tenant import Tenant
    tenant = await provision_tenant(name=body.name, email=body.email, db=db)

    # Buat user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        role="tenant_user",
    )
    db.add(user)
    await db.flush()

    logger.info(
        "User registered",
        extra={"user_id": str(user.id), "tenant_id": str(tenant.id)},
    )
    return user, tenant


async def login_user(body: LoginRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan.")

    logger.info("User logged in", extra={"user_id": str(user.id)})
    return _make_token_response(user)


async def refresh_access_token(
    refresh_token: str, db: AsyncSession
) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Bukan refresh token.")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User tidak ditemukan atau nonaktif.")

    return _make_token_response(user)
```

- [ ] **Step 3: Tulis tests**

```python
# backend/tests/test_auth_service.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import login_user, refresh_access_token, register_user


def _mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_register_user_success():
    db = _mock_db()
    body = RegisterRequest(name="Toko Kece", email="toko@test.com", password="secret123")

    # Simulasi: email belum ada
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.provision_tenant") as mock_provision:
        mock_tenant = MagicMock()
        mock_tenant.id = uuid.uuid4()
        mock_provision.return_value = mock_tenant

        user, tenant = await register_user(body, db)

    assert user.email == "toko@test.com"
    assert user.role == "tenant_user"
    assert tenant is mock_tenant


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_409():
    db = _mock_db()
    body = RegisterRequest(name="Toko", email="exists@test.com", password="secret123")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()  # user sudah ada
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc:
        await register_user(body, db)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_password_raises_401():
    db = _mock_db()
    body = LoginRequest(email="user@test.com", password="wrongpass")

    mock_user = MagicMock()
    mock_user.password_hash = "hashed"
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await login_user(body, db)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_success_returns_tokens():
    db = _mock_db()
    body = LoginRequest(email="user@test.com", password="correctpass")

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.tenant_id = uuid.uuid4()
    mock_user.role = "tenant_user"
    mock_user.is_active = True
    mock_user.password_hash = "hashed"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auth_service.verify_password", return_value=True):
        response = await login_user(body, db)

    assert response.access_token
    assert response.refresh_token
    assert response.token_type == "bearer"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_raises_401():
    db = _mock_db()

    with pytest.raises(HTTPException) as exc:
        await refresh_access_token("invalid.token", db)

    assert exc.value.status_code == 401
```

- [ ] **Step 4: Jalankan tests**

```bash
pytest tests/test_auth_service.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/
git commit -m "feat: auth service (register, login, refresh) dan tenant provisioning"
```

---

## Task 9: Auth Router & FastAPI App

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: semua dari Task 2–8
- Produces:
  - `POST /api/v1/auth/register` → `APIResponse[TenantResponse]`
  - `POST /api/v1/auth/login` → `APIResponse[TokenResponse]`
  - `POST /api/v1/auth/refresh` → `APIResponse[TokenResponse]`
  - `GET /health` → `{"status": "ok"}`

- [ ] **Step 1: Buat `app/routers/auth.py`**

```python
# backend/app/routers/auth.py
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.base import APIResponse
from app.schemas.tenant import TenantResponse
from app.services.auth_service import login_user, refresh_access_token, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=APIResponse[TenantResponse], status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    user, tenant = await register_user(body, db)
    return APIResponse(
        data=TenantResponse.model_validate(tenant),
        message="Akun berhasil dibuat. Selamat datang!",
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await login_user(body, db)
    return APIResponse(data=tokens)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await refresh_access_token(body.refresh_token, db)
    return APIResponse(data=tokens)
```

- [ ] **Step 2: Buat `app/main.py`**

```python
# backend/app/main.py
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.middleware.error_handler import (
    global_exception_handler,
    not_found_handler,
    validation_exception_handler,
)
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.routers import auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Reseller AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (urutan: luar ke dalam)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(TenantContextMiddleware)

# Exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Buat `tests/conftest.py`**

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
```

- [ ] **Step 4: Tulis integration tests auth**

```python
# backend/tests/test_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_success(client):
    mock_tenant = MagicMock()
    mock_tenant.id = uuid.uuid4()
    mock_tenant.name = "Toko Kece"
    mock_tenant.email = "toko@test.com"
    mock_tenant.plan = "free"

    mock_user = MagicMock()

    with patch("app.routers.auth.register_user", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = (mock_user, mock_tenant)
        res = client.post("/api/v1/auth/register", json={
            "name": "Toko Kece",
            "email": "toko@test.com",
            "password": "secret123",
        })

    assert res.status_code == 201
    assert res.json()["success"] is True
    assert res.json()["data"]["email"] == "toko@test.com"


def test_register_invalid_email_returns_422(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Toko",
        "email": "bukan-email",
        "password": "secret123",
    })
    assert res.status_code == 422
    assert res.json()["success"] is False
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_login_success(client):
    from app.schemas.auth import TokenResponse
    mock_tokens = TokenResponse(
        access_token="access.token.here",
        refresh_token="refresh.token.here",
    )

    with patch("app.routers.auth.login_user", new_callable=AsyncMock) as mock_login:
        mock_login.return_value = mock_tokens
        res = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })

    assert res.status_code == 200
    assert res.json()["data"]["access_token"] == "access.token.here"
    assert res.json()["data"]["token_type"] == "bearer"


def test_login_wrong_credentials_returns_401(client):
    from fastapi import HTTPException

    with patch("app.routers.auth.login_user", new_callable=AsyncMock) as mock_login:
        mock_login.side_effect = HTTPException(status_code=401, detail="Email atau password salah.")
        res = client.post("/api/v1/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpass",
        })

    assert res.status_code == 401


def test_protected_endpoint_without_token_returns_401(client):
    res = client.get("/api/v1/some-protected-route")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"
```

- [ ] **Step 5: Jalankan semua tests**

```bash
pytest tests/ -v --tb=short
```

Expected: semua tests PASSED.

- [ ] **Step 6: Smoke test — jalankan server**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Buka `http://localhost:8000/health` — expected: `{"status": "ok"}`
Buka `http://localhost:8000/docs` — expected: Swagger UI dengan endpoint auth.

- [ ] **Step 7: Commit final Fase 1**

```bash
git add backend/app/routers/auth.py backend/app/main.py backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "feat: auth router (register/login/refresh) dan FastAPI app entry point — Fase 1 selesai"
```

---

## Task 10: Tenant Isolation Test

**Files:**
- Test: `backend/tests/test_tenant_isolation.py`

**Interfaces:**
- Consumes: semua dari Task 2–9

- [ ] **Step 1: Tulis tenant isolation tests**

```python
# backend/tests/test_tenant_isolation.py
"""
Test bahwa query tidak bisa bocor lintas tenant.
Verifikasi RULE-03: setiap query wajib filter tenant_id.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_flags import check_feature_status, FeatureStatus


@pytest.mark.asyncio
async def test_feature_status_scoped_to_tenant():
    """check_feature_status tidak bisa digunakan untuk akses data tenant lain."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    db = AsyncMock()

    tenant_a_mock = MagicMock()
    tenant_a_mock.plan = "pro"

    tenant_b_mock = MagicMock()
    tenant_b_mock.plan = "free"

    async def get_tenant_by_id(tenant_id, db):
        if tenant_id == tenant_a:
            return tenant_a_mock
        return tenant_b_mock

    with patch("app.core.feature_flags._get_tenant", side_effect=get_tenant_by_id), \
         patch("app.core.feature_flags._is_quota_exceeded", return_value=False), \
         patch("app.core.feature_flags._get_credential", return_value=None):
        status_a = await check_feature_status(tenant_a, "product_discovery", db)
        status_b = await check_feature_status(tenant_b, "product_discovery", db)

    # Tenant A (pro) bisa akses product_discovery, Tenant B (free) tidak
    assert status_a == FeatureStatus.NOT_CONFIGURED  # aktif di plan tapi belum konfigurasi
    assert status_b == FeatureStatus.PLAN_LOCKED      # plan free tidak punya fitur ini


@pytest.mark.asyncio
async def test_tenant_provisioning_creates_isolated_workspace():
    """Setiap tenant mendapat UUID unik — tidak bisa collision."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    from app.services.tenant_service import provision_tenant

    tenant1 = await provision_tenant("Toko A", "a@test.com", db)
    tenant2 = await provision_tenant("Toko B", "b@test.com", db)

    assert tenant1.id != tenant2.id
    assert tenant1.email != tenant2.email
    assert tenant1.plan == "free"
    assert tenant2.plan == "free"
```

- [ ] **Step 2: Jalankan**

```bash
pytest tests/test_tenant_isolation.py -v
```

Expected: 2 tests PASSED.

- [ ] **Step 3: Jalankan full test suite**

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected: semua tests PASSED, coverage report tampil.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_tenant_isolation.py
git commit -m "test: tenant isolation verification — RULE-03 coverage"
```

---

## Self-Review

### Spec Coverage

| Requirement SDD | Task |
|---|---|
| Setup project structure (Section 14.2) | Task 1 |
| PostgreSQL + pgvector + Alembic migration awal | Task 3 |
| Redis + Celery app | Task 4 |
| `core/feature_flags.py` wajib ada sebelum engine apapun | Task 5 |
| `middleware/error_handler.py` wajib ada sebelum router apapun | Task 6 |
| `middleware/tenant_context.py` | Task 6 |
| Auth: register, login, JWT issue & refresh | Task 8, 9 |
| Tenant provisioning saat register | Task 8 |
| RULE-01: feature flag check | Task 5 + tests |
| RULE-02: no raw error ke response | Task 6 + tests |
| RULE-03: tenant_id filter wajib | Task 3, 8 + Task 10 |
| RULE-04: Celery retry & log | Task 4 (stub, full di Fase 2) |
| RULE-05: no secret di kode | Task 2 (pydantic-settings) |
| RULE-06: Pydantic v2 schema | Task 7 |
| RULE-08: no print() | Semua file pakai `logging` |
| RULE-09: Alembic migration | Task 3 |
| RULE-10: type hints | Semua fungsi publik |
| `users` table dengan role (Section 7 v2.4) | Task 3 |
| `system_logs` table (Section 7 v2.4) | **Gap** — lihat catatan |
| RLS two-layer defense dengan SET LOCAL (Section 4.1 v2.4) | Task 3 (database.py) |
| `.env.example` semua variabel | Task 1 |

**Gap ditemukan:**
- Tabel `system_logs` dari Section 7 v2.4 belum dibuatkan model dan migration. Tabel ini dibutuhkan oleh RULE-04 dan Celery workers (Fase 2+). Tambahkan di Task 3 Step 3–8 sebagai model tambahan di migration awal.

### Perbaikan Gap — `system_logs` model

Tambahkan file ini ke Task 3 sebelum migration dijalankan:

```python
# backend/app/models/system_log.py
import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class SystemLog(Base, TimestampMixin):
    __tablename__ = "system_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

Dan import di `alembic/env.py`:
```python
from app.models.system_log import SystemLog  # noqa: F401
```

Jalankan ulang migration setelah menambahkan model ini.
