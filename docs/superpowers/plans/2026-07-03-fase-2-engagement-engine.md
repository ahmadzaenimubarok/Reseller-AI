# Fase 2 — Engagement Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun Engagement Engine backend yang menerima webhook Facebook (komentar + Messenger DM), mengklasifikasi intent via OpenRouter, generate auto-reply dengan RAG context, dan mendukung human takeover per conversation.

**Architecture:** Webhook Facebook diverifikasi lalu event dipush ke Redis queue. Celery `engagement_worker` memproses event async: cek feature flag → cek human takeover → enrich dengan RAG (pgvector) → classify intent via LLM → eskalasi jika perlu → generate & kirim reply via Meta Graph API. Semua terpusat di `openai_service.py` yang abstrak terhadap provider (OpenRouter dev / OpenAI prod via env vars).

**Tech Stack:** FastAPI, Celery 5, Redis, SQLAlchemy async, pgvector, `openai` Python SDK (dipakai untuk OpenRouter juga via `base_url`), Meta Graph API (Facebook + Messenger), httpx

## Global Constraints

- RULE-01: setiap fungsi yang menyentuh integrasi eksternal wajib panggil `check_feature_status()` sebelum eksekusi
- RULE-02: tidak ada raw error ke response — semua ditangkap error_handler middleware
- RULE-03: setiap query DB wajib filter `tenant_id`
- RULE-04: semua Celery task wajib `max_retries=3`, `retry_backoff=True`, log ke `system_logs`
- RULE-05: tidak ada secret di kode — semua dari env vars via `get_settings()`
- RULE-06: semua input via Pydantic v2 schema
- RULE-08: tidak ada `print()` — gunakan `logging` terstruktur
- RULE-09: perubahan schema DB via Alembic migration
- RULE-10: semua fungsi publik wajib type hint
- Platform scope Fase 2: Facebook Page (komentar) + Messenger (DM) saja
- AI provider: OpenRouter untuk dev, abstraksi via `base_url` + `api_key` env vars
- Human takeover: kolom `is_human_takeover` di `conversations`, toggle via `PATCH /api/v1/conversations/{id}/takeover`
- Eskalasi otomatis: topik blacklist dari `tenant.ai_config["escalation_topics"]`

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                    # MODIFY: tambah OPENROUTER_API_KEY, OPENROUTER_BASE_URL, AI_MODEL_FAST, AI_MODEL_QUALITY, META_VERIFY_TOKEN
│   ├── models/
│   │   ├── customer.py                  # CREATE: Customer model
│   │   └── conversation.py             # CREATE: Conversation model (+ is_human_takeover)
│   ├── schemas/
│   │   ├── webhook.py                   # CREATE: FacebookWebhookPayload, WebhookEntry, WebhookMessage
│   │   └── conversation.py             # CREATE: ConversationResponse, TakeoverRequest
│   ├── routers/
│   │   ├── webhooks.py                  # CREATE: GET/POST /webhooks/facebook (verify + receive)
│   │   └── conversations.py            # CREATE: GET /conversations, PATCH /conversations/{id}/takeover
│   ├── services/
│   │   ├── openai_service.py           # CREATE: LLM wrapper (OpenRouter/OpenAI agnostic)
│   │   ├── rag_service.py              # CREATE: pgvector search untuk product context
│   │   ├── facebook_service.py         # CREATE: send_reply() via Meta Graph API
│   │   └── engagement_service.py      # CREATE: orchestrator — intent classify, escalate, reply
│   └── main.py                          # MODIFY: daftarkan router webhooks + conversations
├── workers/
│   └── engagement_worker.py            # MODIFY: implementasi task process_facebook_event()
├── alembic/versions/
│   └── xxxx_add_customers_conversations.py  # CREATE: migration baru
└── tests/
    ├── test_openai_service.py           # CREATE
    ├── test_rag_service.py              # CREATE
    ├── test_engagement_service.py      # CREATE
    ├── test_webhook_router.py          # CREATE
    └── test_conversations_router.py    # CREATE
```

---

## Task 1: Config & Dependencies Update

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Modify: `backend/.env`

**Interfaces:**
- Produces:
  - `settings.OPENROUTER_API_KEY: str`
  - `settings.OPENROUTER_BASE_URL: str`
  - `settings.AI_MODEL_FAST: str`
  - `settings.AI_MODEL_QUALITY: str`
  - `settings.META_VERIFY_TOKEN: str`
  - `settings.META_APP_SECRET: str` (sudah ada)
  - `settings.META_APP_ID: str` (sudah ada)

- [ ] **Step 1: Tambah dependency baru ke `pyproject.toml`**

```toml
# tambahkan ke [project] dependencies:
"openai==1.51.0",
"httpx==0.27.2",   # sudah ada, verifikasi
```

Jalankan:
```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
pip install -q "openai==1.51.0"
```

Expected: installed tanpa error.

- [ ] **Step 2: Update `app/core/config.py`**

```python
# backend/app/core/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # AI Provider (OpenRouter untuk dev, OpenAI untuk prod)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL_FAST: str = "meta-llama/llama-3.1-8b-instruct:free"
    AI_MODEL_QUALITY: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Meta (Facebook / Instagram)
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""          # token untuk verifikasi webhook Facebook

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

- [ ] **Step 3: Update `.env` dan `.env.example`**

Tambahkan ke `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL_FAST=meta-llama/llama-3.1-8b-instruct:free
AI_MODEL_QUALITY=meta-llama/llama-3.1-8b-instruct:free
META_VERIFY_TOKEN=reseller-ai-webhook-verify-secret
```

Tambahkan ke `.env.example`:
```bash
# AI Provider
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL_FAST=meta-llama/llama-3.1-8b-instruct:free
AI_MODEL_QUALITY=meta-llama/llama-3.1-8b-instruct:free

# Facebook Webhook
META_VERIFY_TOKEN=
```

- [ ] **Step 4: Verifikasi config load tanpa error**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
python -c "from app.core.config import get_settings; s = get_settings(); print(s.AI_MODEL_FAST)"
```

Expected: `meta-llama/llama-3.1-8b-instruct:free`

- [ ] **Step 5: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/core/config.py backend/pyproject.toml backend/.env.example
git commit -m "feat: tambah config OpenRouter, AI model, dan META_VERIFY_TOKEN"
```

---

## Task 2: Models & Migration (Customer + Conversation)

**Files:**
- Create: `backend/app/models/customer.py`
- Create: `backend/app/models/conversation.py`
- Modify: `backend/alembic/env.py` (import model baru)
- Create: `backend/alembic/versions/xxxx_add_customers_conversations.py`

**Interfaces:**
- Produces:
  - `Customer` model — `id`, `tenant_id`, `platform_user_id`, `platform`, `name`, `handle`, `first_seen`, `tags`
  - `Conversation` model — `id`, `tenant_id`, `customer_id`, `platform`, `channel_type`, `platform_message_id`, `message_in`, `message_out`, `intent`, `sentiment`, `is_human_takeover`, `escalation_reason`, `created_at`

- [ ] **Step 1: Buat `app/models/customer.py`**

```python
# backend/app/models/customer.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'facebook' | 'messenger' | 'instagram' | 'whatsapp'
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    tags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
```

- [ ] **Step 2: Buat `app/models/conversation.py`**

```python
# backend/app/models/conversation.py
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'facebook' | 'messenger'
    channel_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'comment' | 'dm'
    platform_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # untuk dedup — cegah proses event yang sama dua kali
    message_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_out: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'tanya_info' | 'niat_beli' | 'komplain' | 'spam'
    sentiment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'positive' | 'neutral' | 'negative'
    is_human_takeover: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    escalation_reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
```

- [ ] **Step 3: Update `alembic/env.py` — import model baru**

Tambahkan dua baris import setelah baris import `SystemLog`:

```python
from app.models.customer import Customer  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
```

- [ ] **Step 4: Generate dan jalankan migration**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_customers_and_conversations"
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 353710d138e6 -> <rev>, add_customers_and_conversations
```

Verifikasi:
```bash
psql "postgresql://postgres:1@localhost:5432/reseller_ai" -c "\dt"
```

Expected: tabel `customers` dan `conversations` muncul.

- [ ] **Step 5: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/models/customer.py backend/app/models/conversation.py backend/alembic/
git commit -m "feat: model Customer dan Conversation + Alembic migration"
```

---

## Task 3: OpenAI Service (Provider Abstraction)

**Files:**
- Create: `backend/app/services/openai_service.py`
- Create: `backend/tests/test_openai_service.py`

**Interfaces:**
- Consumes: `get_settings()` dari Task 1
- Produces:
  - `get_llm_client() -> openai.AsyncOpenAI` — client siap pakai (OpenRouter atau OpenAI)
  - `classify_intent(message: str, tenant_context: str) -> IntentResult`
  - `generate_reply(message: str, context: str, tone: str) -> str`
  - `IntentResult` — dataclass: `intent: str`, `sentiment: str`, `confidence: float`

- [ ] **Step 1: Tulis failing tests**

```python
# backend/tests/test_openai_service.py
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.openai_service import IntentResult, classify_intent, generate_reply


@pytest.mark.asyncio
async def test_classify_intent_returns_intent_result():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"intent": "tanya_info", "sentiment": "neutral", "confidence": 0.92}'
    )

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        result = await classify_intent(
            message="Harga berapa kak?",
            tenant_context="Toko fashion wanita",
        )

    assert isinstance(result, IntentResult)
    assert result.intent == "tanya_info"
    assert result.sentiment == "neutral"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_invalid_json():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ini bukan json"

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        result = await classify_intent("pesan", "context")

    # fallback aman — tidak crash, intent default
    assert result.intent == "tanya_info"
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_generate_reply_returns_string():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Halo kak! Ada yang bisa dibantu? 😊"

    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        reply = await generate_reply(
            message="Halo ada diskon ga?",
            context="Produk: Tas Rajut, harga Rp 150.000",
            tone="casual",
        )

    assert isinstance(reply, str)
    assert len(reply) > 0


@pytest.mark.asyncio
async def test_generate_reply_fallback_on_exception():
    with patch("app.services.openai_service.get_llm_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API down")
        )
        mock_client_fn.return_value = mock_client

        reply = await generate_reply("pesan", "context", "casual")

    # fallback — tidak crash, kembalikan pesan netral
    assert reply == "Halo! Terima kasih sudah menghubungi kami. Tim kami akan segera membalas pesanmu ya 🙏"
```

- [ ] **Step 2: Jalankan test — pastikan FAIL**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
pytest tests/test_openai_service.py -v 2>&1 | head -20
```

Expected: `ImportError` atau `ModuleNotFoundError`.

- [ ] **Step 3: Buat `app/services/openai_service.py`**

```python
# backend/app/services/openai_service.py
import json
import logging
from dataclasses import dataclass

import openai

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Halo! Terima kasih sudah menghubungi kami. Tim kami akan segera membalas pesanmu ya 🙏"

INTENT_SYSTEM_PROMPT = """Kamu adalah classifier intent untuk customer service toko online Indonesia.
Klasifikasikan pesan customer ke salah satu intent berikut:
- tanya_info: pertanyaan tentang produk, harga, stok, pengiriman
- niat_beli: menunjukkan minat beli, mau order, tanya cara beli
- komplain: keluhan, ketidakpuasan, masalah pesanan
- spam: pesan tidak relevan, promosi, atau tidak bermakna

Kembalikan HANYA JSON valid dengan format:
{"intent": "<salah satu dari 4 intent>", "sentiment": "<positive|neutral|negative>", "confidence": <0.0-1.0>}"""

REPLY_SYSTEM_PROMPT = """Kamu adalah asisten customer service toko online Indonesia yang ramah dan helpful.
Balas pesan customer dengan gaya bahasa: {tone}.
Gunakan HANYA informasi dari konteks produk yang diberikan — jangan membuat klaim yang tidak ada di konteks.
Jika informasi tidak tersedia di konteks, katakan kamu akan cek dulu.
Balas dalam bahasa Indonesia yang natural, singkat (maks 3 kalimat), dan tidak berlebihan."""


@dataclass
class IntentResult:
    intent: str
    sentiment: str
    confidence: float


def get_llm_client() -> openai.AsyncOpenAI:
    settings = get_settings()
    # Gunakan OpenRouter jika API key tersedia, fallback ke OpenAI
    if settings.OPENROUTER_API_KEY:
        return openai.AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
    return openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


async def classify_intent(message: str, tenant_context: str) -> IntentResult:
    settings = get_settings()
    client = get_llm_client()
    try:
        response = await client.chat.completions.create(
            model=settings.AI_MODEL_FAST,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Konteks toko: {tenant_context}\n\nPesan customer: {message}",
                },
            ],
            temperature=0.1,
            max_tokens=100,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw.strip())
        return IntentResult(
            intent=data.get("intent", "tanya_info"),
            sentiment=data.get("sentiment", "neutral"),
            confidence=float(data.get("confidence", 0.5)),
        )
    except json.JSONDecodeError:
        logger.warning("classify_intent: JSON parse gagal", extra={"raw": raw[:200]})
        return IntentResult(intent="tanya_info", sentiment="neutral", confidence=0.0)
    except Exception:
        logger.exception("classify_intent error")
        return IntentResult(intent="tanya_info", sentiment="neutral", confidence=0.0)


async def generate_reply(message: str, context: str, tone: str) -> str:
    settings = get_settings()
    client = get_llm_client()
    try:
        system = REPLY_SYSTEM_PROMPT.format(tone=tone)
        response = await client.chat.completions.create(
            model=settings.AI_MODEL_FAST,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Konteks produk:\n{context}\n\nPesan customer:\n{message}",
                },
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content or FALLBACK_REPLY
    except Exception:
        logger.exception("generate_reply error")
        return FALLBACK_REPLY
```

- [ ] **Step 4: Jalankan tests**

```bash
pytest tests/test_openai_service.py -v
```

Expected:
```
test_openai_service.py::test_classify_intent_returns_intent_result PASSED
test_openai_service.py::test_classify_intent_fallback_on_invalid_json PASSED
test_openai_service.py::test_generate_reply_returns_string PASSED
test_openai_service.py::test_generate_reply_fallback_on_exception PASSED
4 passed
```

- [ ] **Step 5: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/services/openai_service.py backend/tests/test_openai_service.py
git commit -m "feat: openai_service.py abstraksi provider (OpenRouter/OpenAI) + intent classifier + reply generator"
```

---

## Task 4: RAG Service (pgvector Product Context)

**Files:**
- Create: `backend/app/services/rag_service.py`
- Create: `backend/tests/test_rag_service.py`

**Interfaces:**
- Consumes: `AsyncSession` dari database.py
- Produces:
  - `get_product_context(tenant_id: str, query: str, db: AsyncSession) -> str`
    — kembalikan string teks konteks produk (maks 5 hasil terdekat, digabung jadi satu teks)

**Catatan:** Di Fase 2 embedding belum aktif (butuh API key berbayar). `get_product_context` menggunakan **keyword fallback** — ambil produk aktif tenant dari tabel `products` (belum dibuat). Jika tabel `products` belum ada, kembalikan string kosong. Implementasi pgvector penuh ditambah di Fase 4.

- [ ] **Step 1: Buat model `Product` minimal untuk RAG fallback**

```python
# backend/app/models/product.py
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    margin_estimate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    affiliate_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # 'active' | 'inactive'
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Import di `alembic/env.py`:
```python
from app.models.product import Product  # noqa: F401
```

Jalankan migration:
```bash
alembic revision --autogenerate -m "add_products"
alembic upgrade head
```

- [ ] **Step 2: Tulis failing tests**

```python
# backend/tests/test_rag_service.py
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rag_service import get_product_context


@pytest.mark.asyncio
async def test_get_product_context_returns_string_with_products():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    mock_product = MagicMock()
    mock_product.name = "Tas Rajut Aesthetic"
    mock_product.description = "Tas rajut handmade, tersedia 5 warna"
    mock_product.base_price = 150000
    mock_product.affiliate_link = "https://shopee.co.id/tas-rajut"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_product]
    db.execute = AsyncMock(return_value=mock_result)

    context = await get_product_context(tenant_id, "tas rajut", db)

    assert "Tas Rajut Aesthetic" in context
    assert isinstance(context, str)


@pytest.mark.asyncio
async def test_get_product_context_returns_empty_when_no_products():
    db = AsyncMock()
    tenant_id = str(uuid.uuid4())

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    context = await get_product_context(tenant_id, "query apapun", db)

    assert context == ""


@pytest.mark.asyncio
async def test_get_product_context_safe_on_db_error():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("DB error"))
    tenant_id = str(uuid.uuid4())

    context = await get_product_context(tenant_id, "query", db)

    assert context == ""
```

- [ ] **Step 3: Jalankan test — pastikan FAIL**

```bash
pytest tests/test_rag_service.py -v 2>&1 | head -10
```

Expected: `ImportError`.

- [ ] **Step 4: Buat `app/services/rag_service.py`**

```python
# backend/app/services/rag_service.py
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

logger = logging.getLogger(__name__)

MAX_PRODUCTS = 5


async def get_product_context(
    tenant_id: str, query: str, db: AsyncSession
) -> str:
    """
    Kembalikan konteks produk sebagai teks untuk RAG prompt.
    Fase 2: keyword fallback — ambil produk aktif tenant (maks 5).
    Fase 4: ganti dengan pgvector similarity search.
    """
    try:
        result = await db.execute(
            select(Product)
            .where(
                Product.tenant_id == uuid.UUID(tenant_id),
                Product.status == "active",
            )
            .limit(MAX_PRODUCTS)
        )
        products = result.scalars().all()

        if not products:
            return ""

        lines = []
        for p in products:
            parts = [f"Produk: {p.name}"]
            if p.description:
                parts.append(f"Deskripsi: {p.description}")
            if p.base_price:
                parts.append(f"Harga: Rp {int(p.base_price):,}")
            if p.affiliate_link:
                parts.append(f"Link beli: {p.affiliate_link}")
            lines.append(" | ".join(parts))

        return "\n".join(lines)

    except Exception:
        logger.exception(
            "get_product_context error", extra={"tenant_id": tenant_id}
        )
        return ""
```

- [ ] **Step 5: Jalankan tests**

```bash
pytest tests/test_rag_service.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/models/product.py backend/app/services/rag_service.py backend/tests/test_rag_service.py backend/alembic/
git commit -m "feat: Product model, RAG service (keyword fallback), migration products"
```

---

## Task 5: Facebook Service (Send Reply via Meta Graph API)

**Files:**
- Create: `backend/app/services/facebook_service.py`
- Create: `backend/tests/test_facebook_service.py`

**Interfaces:**
- Produces:
  - `send_comment_reply(page_token: str, comment_id: str, message: str) -> bool`
  - `send_messenger_reply(page_token: str, recipient_id: str, message: str) -> bool`

- [ ] **Step 1: Tulis failing tests**

```python
# backend/tests/test_facebook_service.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.facebook_service import send_comment_reply, send_messenger_reply


@pytest.mark.asyncio
async def test_send_comment_reply_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "comment-123"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_comment_reply(
            page_token="token123",
            comment_id="comment-abc",
            message="Halo kak! Ada yang bisa dibantu?",
        )

    assert result is True


@pytest.mark.asyncio
async def test_send_comment_reply_returns_false_on_error():
    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connection failed"))
        mock_client_cls.return_value = mock_client

        result = await send_comment_reply("token", "comment-id", "pesan")

    assert result is False


@pytest.mark.asyncio
async def test_send_messenger_reply_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"recipient_id": "user-123", "message_id": "mid.123"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await send_messenger_reply(
            page_token="token123",
            recipient_id="user-abc",
            message="Halo! Terima kasih sudah DM kami.",
        )

    assert result is True


@pytest.mark.asyncio
async def test_send_messenger_reply_returns_false_on_error():
    with patch("app.services.facebook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_client_cls.return_value = mock_client

        result = await send_messenger_reply("token", "user-id", "pesan")

    assert result is False
```

- [ ] **Step 2: Buat `app/services/facebook_service.py`**

```python
# backend/app/services/facebook_service.py
import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


async def send_comment_reply(
    page_token: str, comment_id: str, message: str
) -> bool:
    """Balas komentar Facebook via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"access_token": page_token},
                json={"message": message},
            )
            response.raise_for_status()
            logger.info(
                "Comment reply sent",
                extra={"comment_id": comment_id},
            )
            return True
    except Exception:
        logger.exception(
            "send_comment_reply failed", extra={"comment_id": comment_id}
        )
        return False


async def send_messenger_reply(
    page_token: str, recipient_id: str, message: str
) -> bool:
    """Kirim pesan Messenger via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/me/messages"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"access_token": page_token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                },
            )
            response.raise_for_status()
            logger.info(
                "Messenger reply sent",
                extra={"recipient_id": recipient_id},
            )
            return True
    except Exception:
        logger.exception(
            "send_messenger_reply failed", extra={"recipient_id": recipient_id}
        )
        return False
```

- [ ] **Step 3: Jalankan tests**

```bash
pytest tests/test_facebook_service.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/services/facebook_service.py backend/tests/test_facebook_service.py
git commit -m "feat: facebook_service — send_comment_reply dan send_messenger_reply via Meta Graph API"
```

---

## Task 6: Engagement Service (Orchestrator)

**Files:**
- Create: `backend/app/services/engagement_service.py`
- Create: `backend/tests/test_engagement_service.py`

**Interfaces:**
- Consumes:
  - `classify_intent(message, tenant_context) -> IntentResult` dari Task 3
  - `generate_reply(message, context, tone) -> str` dari Task 3
  - `get_product_context(tenant_id, query, db) -> str` dari Task 4
  - `send_comment_reply(page_token, comment_id, message) -> bool` dari Task 5
  - `send_messenger_reply(page_token, recipient_id, message) -> bool` dari Task 5
  - `check_feature_status(tenant_id, feature, db) -> FeatureStatus` dari Fase 1
  - `Customer` model dari Task 2
  - `Conversation` model dari Task 2
  - `Tenant` model dari Fase 1
  - `TenantCredential` model dari Fase 1
- Produces:
  - `process_facebook_comment(tenant_id: str, event: dict, db: AsyncSession) -> None`
  - `process_messenger_message(tenant_id: str, event: dict, db: AsyncSession) -> None`

- [ ] **Step 1: Tulis failing tests**

```python
# backend/tests/test_engagement_service.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.engagement_service import (
    process_facebook_comment,
    process_messenger_message,
)


def _mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_tenant(tone: str = "casual", escalation_topics: list | None = None) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.plan = "pro"
    t.ai_config = {
        "tone": tone,
        "escalation_topics": escalation_topics or ["penipuan", "refund"],
    }
    return t


def _mock_credential() -> MagicMock:
    c = MagicMock()
    c.access_token_encrypted = "encrypted-token"
    c.is_expired.return_value = False
    return c


@pytest.mark.asyncio
async def test_process_facebook_comment_sends_reply():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-123",
        "message": "Kak harga berapa?",
        "from_id": "user-456",
        "from_name": "Budi",
        "post_id": "post-789",
    }

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_product_context", return_value="Produk: Tas Rajut | Harga: Rp 150.000"), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.generate_reply", return_value="Harga Rp 150.000 kak!"), \
         patch("app.services.engagement_service.send_comment_reply", return_value=True), \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE

        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="tanya_info", sentiment="neutral", confidence=0.9
        )

        await process_facebook_comment(tenant_id, event, db)

    # Harus ada conversation yang disimpan ke DB
    db.add.assert_called()


@pytest.mark.asyncio
async def test_process_facebook_comment_skips_when_feature_not_active():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    event = {"comment_id": "c1", "message": "test", "from_id": "u1", "from_name": "User", "post_id": "p1"}

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service.send_comment_reply") as mock_send:

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.NOT_CONFIGURED

        await process_facebook_comment(tenant_id, event, db)

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_facebook_comment_escalates_on_blacklist_topic():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant(escalation_topics=["refund", "penipuan"])
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-esc",
        "message": "Ini penipuan! Saya mau refund!",
        "from_id": "user-789",
        "from_name": "Andi",
        "post_id": "post-111",
    }

    saved_conversations = []

    def capture_add(obj):
        saved_conversations.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=None), \
         patch("app.services.engagement_service.get_product_context", return_value=""), \
         patch("app.services.engagement_service.classify_intent") as mock_intent, \
         patch("app.services.engagement_service.send_comment_reply") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE
        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        from app.services.openai_service import IntentResult
        mock_intent.return_value = IntentResult(
            intent="komplain", sentiment="negative", confidence=0.95
        )

        await process_facebook_comment(tenant_id, event, db)

    # Auto-reply tidak dikirim — eskalasi ke human
    mock_send.assert_not_called()

    # Conversation disimpan dengan is_human_takeover=True
    conv_objects = [o for o in saved_conversations if hasattr(o, "is_human_takeover")]
    assert any(o.is_human_takeover is True for o in conv_objects)


@pytest.mark.asyncio
async def test_process_facebook_comment_skips_if_already_human_takeover():
    db = _mock_db()
    tenant_id = str(uuid.uuid4())
    tenant = _mock_tenant()
    credential = _mock_credential()

    event = {
        "comment_id": "cmnt-ht",
        "message": "Halo lagi kak",
        "from_id": "user-ht",
        "from_name": "Cici",
        "post_id": "post-ht",
    }

    existing_conv = MagicMock()
    existing_conv.is_human_takeover = True

    with patch("app.services.engagement_service.check_feature_status") as mock_flag, \
         patch("app.services.engagement_service._get_tenant", return_value=tenant), \
         patch("app.services.engagement_service._get_facebook_credential", return_value=credential), \
         patch("app.services.engagement_service._get_or_create_customer") as mock_customer, \
         patch("app.services.engagement_service._get_conversation_by_platform_id", return_value=existing_conv), \
         patch("app.services.engagement_service.send_comment_reply") as mock_send, \
         patch("app.services.engagement_service.decrypt_credential", return_value="real-token"):

        from app.core.feature_flags import FeatureStatus
        mock_flag.return_value = FeatureStatus.ACTIVE
        mock_customer.return_value = MagicMock(id=uuid.uuid4())

        await process_facebook_comment(tenant_id, event, db)

    mock_send.assert_not_called()
```

- [ ] **Step 2: Buat `app/services/engagement_service.py`**

```python
# backend/app/services/engagement_service.py
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import FeatureStatus, check_feature_status, log_skip
from app.core.security import decrypt_credential
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.system_log import SystemLog
from app.models.tenant import Tenant
from app.models.tenant_credential import TenantCredential
from app.services.facebook_service import send_comment_reply, send_messenger_reply
from app.services.openai_service import IntentResult, classify_intent, generate_reply
from app.services.rag_service import get_product_context

logger = logging.getLogger(__name__)


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
    )
    return result.scalar_one_or_none()


async def _get_facebook_credential(
    tenant_id: str, db: AsyncSession
) -> TenantCredential | None:
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_customer(
    tenant_id: str,
    platform_user_id: str,
    platform: str,
    name: str | None,
    db: AsyncSession,
) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == uuid.UUID(tenant_id),
            Customer.platform_user_id == platform_user_id,
            Customer.platform == platform,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(
            tenant_id=uuid.UUID(tenant_id),
            platform_user_id=platform_user_id,
            platform=platform,
            name=name,
        )
        db.add(customer)
        await db.flush()
    return customer


async def _get_conversation_by_platform_id(
    tenant_id: str, platform_message_id: str, db: AsyncSession
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == uuid.UUID(tenant_id),
            Conversation.platform_message_id == platform_message_id,
        )
    )
    return result.scalar_one_or_none()


def _should_escalate(message: str, intent_result: IntentResult, escalation_topics: list[str]) -> tuple[bool, str]:
    """Kembalikan (should_escalate, reason)."""
    msg_lower = message.lower()
    for topic in escalation_topics:
        if topic.lower() in msg_lower:
            return True, f"blacklist_topic:{topic}"
    if intent_result.intent == "komplain" and intent_result.sentiment == "negative":
        return True, "negative_complaint"
    return False, ""


async def _save_system_log(
    tenant_id: str,
    action: str,
    status: str,
    context: dict,
    db: AsyncSession,
) -> None:
    log = SystemLog(
        tenant_id=uuid.UUID(tenant_id),
        engine="engagement_engine",
        action=action,
        status=status,
        context=context,
    )
    db.add(log)


async def process_facebook_comment(
    tenant_id: str, event: dict, db: AsyncSession
) -> None:
    """
    Proses event komentar Facebook untuk satu tenant.
    event keys: comment_id, message, from_id, from_name, post_id
    """
    comment_id: str = event["comment_id"]
    message: str = event["message"]
    from_id: str = event["from_id"]
    from_name: str | None = event.get("from_name")

    # RULE-01: cek feature flag
    status = await check_feature_status(tenant_id, "facebook_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "facebook_reply", status)
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Tenant not found", extra={"tenant_id": tenant_id})
        return

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(tenant_id, "comment_reply", "skipped",
                               {"reason": "no_credential", "comment_id": comment_id}, db)
        return

    # Dedup: skip jika sudah pernah diproses
    existing = await _get_conversation_by_platform_id(tenant_id, comment_id, db)
    if existing is not None:
        if existing.is_human_takeover:
            logger.info("Skipping — human takeover active", extra={"comment_id": comment_id})
            return
        # Sudah diproses sebelumnya
        return

    customer = await _get_or_create_customer(tenant_id, from_id, "facebook", from_name, db)

    # RAG context
    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    # Classify intent
    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    page_token = decrypt_credential(credential.access_token_encrypted)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            platform="facebook",
            channel_type="comment",
            platform_message_id=comment_id,
            message_in=message,
            message_out=None,
            intent=intent_result.intent,
            sentiment=intent_result.sentiment,
            is_human_takeover=True,
            escalation_reason=escalation_reason,
        )
        db.add(conv)
        await _save_system_log(tenant_id, "comment_escalated", "success",
                               {"comment_id": comment_id, "reason": escalation_reason}, db)
        logger.info("Conversation escalated to human",
                    extra={"tenant_id": tenant_id, "reason": escalation_reason})
        return

    # Generate dan kirim reply
    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone)
    sent = await send_comment_reply(page_token, comment_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        platform="facebook",
        channel_type="comment",
        platform_message_id=comment_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    await _save_system_log(
        tenant_id, "comment_reply", "success" if sent else "failed",
        {"comment_id": comment_id, "sent": sent}, db,
    )


async def process_messenger_message(
    tenant_id: str, event: dict, db: AsyncSession
) -> None:
    """
    Proses event Messenger DM untuk satu tenant.
    event keys: message_id, message, sender_id
    """
    message_id: str = event["message_id"]
    message: str = event["message"]
    sender_id: str = event["sender_id"]

    status = await check_feature_status(tenant_id, "facebook_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "facebook_reply", status)
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        return

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(tenant_id, "messenger_reply", "skipped",
                               {"reason": "no_credential", "message_id": message_id}, db)
        return

    existing = await _get_conversation_by_platform_id(tenant_id, message_id, db)
    if existing is not None:
        if existing.is_human_takeover:
            return
        return

    customer = await _get_or_create_customer(tenant_id, sender_id, "messenger", None, db)

    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    page_token = decrypt_credential(credential.access_token_encrypted)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            platform="messenger",
            channel_type="dm",
            platform_message_id=message_id,
            message_in=message,
            message_out=None,
            intent=intent_result.intent,
            sentiment=intent_result.sentiment,
            is_human_takeover=True,
            escalation_reason=escalation_reason,
        )
        db.add(conv)
        await _save_system_log(tenant_id, "messenger_escalated", "success",
                               {"message_id": message_id, "reason": escalation_reason}, db)
        return

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone)
    sent = await send_messenger_reply(page_token, sender_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        platform="messenger",
        channel_type="dm",
        platform_message_id=message_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    await _save_system_log(
        tenant_id, "messenger_reply", "success" if sent else "failed",
        {"message_id": message_id, "sent": sent}, db,
    )
```

- [ ] **Step 3: Jalankan tests**

```bash
pytest tests/test_engagement_service.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/services/engagement_service.py backend/tests/test_engagement_service.py
git commit -m "feat: engagement_service — orchestrator intent/escalate/reply untuk Facebook dan Messenger"
```

---

## Task 7: Celery Engagement Worker

**Files:**
- Modify: `backend/workers/engagement_worker.py`
- Create: `backend/tests/test_engagement_worker.py`

**Interfaces:**
- Consumes:
  - `process_facebook_comment(tenant_id, event, db)` dari Task 6
  - `process_messenger_message(tenant_id, event, db)` dari Task 6
  - `celery_app` dari Fase 1
- Produces:
  - `process_facebook_event.delay(tenant_id, event)` — Celery task, queue "engagement"

- [ ] **Step 1: Implementasi `workers/engagement_worker.py`**

```python
# backend/workers/engagement_worker.py
import asyncio
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.engagement_worker.process_facebook_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_facebook_event(self, tenant_id: str, event: dict) -> None:
    """
    Proses satu event Facebook (komentar atau Messenger DM) untuk tenant.
    event["channel_type"]: "comment" | "dm"
    """
    channel_type = event.get("channel_type", "comment")

    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import AsyncSessionLocal
        from app.services.engagement_service import (
            process_facebook_comment,
            process_messenger_message,
        )

        async with AsyncSessionLocal() as session:
            async with session.begin():
                if channel_type == "comment":
                    await process_facebook_comment(tenant_id, event, session)
                elif channel_type == "dm":
                    await process_messenger_message(tenant_id, event, session)
                else:
                    logger.warning(
                        "Unknown channel_type",
                        extra={"channel_type": channel_type, "tenant_id": tenant_id},
                    )

    try:
        asyncio.run(_run())
        logger.info(
            "Facebook event processed",
            extra={"tenant_id": tenant_id, "channel_type": channel_type},
        )
    except Exception as exc:
        logger.error(
            "process_facebook_event failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise
```

- [ ] **Step 2: Tulis tests**

```python
# backend/tests/test_engagement_worker.py
from unittest.mock import MagicMock, patch
import pytest

from workers.engagement_worker import process_facebook_event


def test_task_is_registered():
    from workers.celery_app import celery_app
    assert "workers.engagement_worker.process_facebook_event" in celery_app.tasks


def test_task_has_retry_config():
    task = process_facebook_event
    assert task.max_retries == 3
    assert task.retry_backoff is True


def test_process_facebook_event_comment():
    tenant_id = "tenant-123"
    event = {
        "channel_type": "comment",
        "comment_id": "c1",
        "message": "test",
        "from_id": "u1",
        "from_name": "User",
        "post_id": "p1",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_facebook_event(tenant_id, event)

    mock_run.assert_called_once()


def test_process_facebook_event_dm():
    tenant_id = "tenant-456"
    event = {
        "channel_type": "dm",
        "message_id": "m1",
        "message": "halo",
        "sender_id": "u2",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_facebook_event(tenant_id, event)

    mock_run.assert_called_once()
```

- [ ] **Step 3: Jalankan tests**

```bash
pytest tests/test_engagement_worker.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/workers/engagement_worker.py backend/tests/test_engagement_worker.py
git commit -m "feat: engagement_worker Celery task dengan retry, backoff, dan log (RULE-04)"
```

---

## Task 8: Webhook Router (Facebook Verify + Receive)

**Files:**
- Create: `backend/app/schemas/webhook.py`
- Create: `backend/app/routers/webhooks.py`
- Modify: `backend/app/middleware/tenant_context.py` (tambah `/webhooks/` ke public paths)
- Modify: `backend/app/main.py` (daftarkan router)
- Create: `backend/tests/test_webhook_router.py`

**Interfaces:**
- Consumes:
  - `process_facebook_event.delay(tenant_id, event)` dari Task 7
  - `get_settings()` dari Task 1
- Produces:
  - `GET /webhooks/facebook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...` → echo challenge
  - `POST /webhooks/facebook?tenant_id=<uuid>` → terima event, push ke queue

**Catatan keamanan:** POST webhook harus verifikasi `X-Hub-Signature-256` header dari Facebook menggunakan `META_APP_SECRET`. Tanpa ini, siapapun bisa kirim event palsu.

- [ ] **Step 1: Buat `app/schemas/webhook.py`**

```python
# backend/app/schemas/webhook.py
from typing import Any
from pydantic import BaseModel


class WebhookVerifyParams(BaseModel):
    hub_mode: str
    hub_verify_token: str
    hub_challenge: str


class FacebookWebhookPayload(BaseModel):
    object: str
    entry: list[dict[str, Any]]
```

- [ ] **Step 2: Buat `app/routers/webhooks.py`**

```python
# backend/app/routers/webhooks.py
import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.schemas.webhook import FacebookWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_fb_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verifikasi X-Hub-Signature-256 dari Facebook."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.get("/facebook", response_class=PlainTextResponse)
async def facebook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Endpoint verifikasi webhook Facebook — dipanggil satu kali saat setup."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Facebook webhook verified")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verify token tidak valid.")


@router.post("/facebook")
async def facebook_receive(
    request: Request,
    tenant_id: str = Query(..., description="UUID tenant pemilik page ini"),
) -> dict:
    """Terima event webhook Facebook (komentar + Messenger DM)."""
    settings = get_settings()
    body = await request.body()

    # Verifikasi signature jika META_APP_SECRET dikonfigurasi
    if settings.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        if not _verify_fb_signature(body, signature, settings.META_APP_SECRET):
            logger.warning(
                "Invalid Facebook webhook signature",
                extra={"tenant_id": tenant_id},
            )
            raise HTTPException(status_code=403, detail="Signature tidak valid.")

    try:
        payload = FacebookWebhookPayload.model_validate_json(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Payload tidak valid.")

    if payload.object != "page":
        return {"status": "ignored", "reason": "object bukan page"}

    from workers.engagement_worker import process_facebook_event

    queued = 0
    for entry in payload.entry:
        # Komentar Facebook
        for change in entry.get("changes", []):
            if change.get("field") == "feed":
                value = change.get("value", {})
                if value.get("item") == "comment":
                    event = {
                        "channel_type": "comment",
                        "comment_id": value.get("comment_id", ""),
                        "message": value.get("message", ""),
                        "from_id": value.get("from", {}).get("id", ""),
                        "from_name": value.get("from", {}).get("name"),
                        "post_id": value.get("post_id", ""),
                    }
                    process_facebook_event.delay(tenant_id, event)
                    queued += 1

        # Messenger DM
        for msg_event in entry.get("messaging", []):
            if "message" in msg_event and not msg_event["message"].get("is_echo"):
                event = {
                    "channel_type": "dm",
                    "message_id": msg_event["message"].get("mid", ""),
                    "message": msg_event["message"].get("text", ""),
                    "sender_id": msg_event.get("sender", {}).get("id", ""),
                }
                process_facebook_event.delay(tenant_id, event)
                queued += 1

    logger.info(
        "Facebook webhook received",
        extra={"tenant_id": tenant_id, "queued": queued},
    )
    return {"status": "ok", "queued": queued}
```

- [ ] **Step 3: Tambah `/webhooks/` ke public paths di `tenant_context.py`**

Ubah baris `PUBLIC_PATHS` di `app/middleware/tenant_context.py`:

```python
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
WEBHOOK_PATH_PREFIX = "/webhooks"
```

Dan di method `dispatch`, tambahkan check:

```python
if path in PUBLIC_PATHS or path in AUTH_PATHS or path.startswith(WEBHOOK_PATH_PREFIX):
    return await call_next(request)
```

- [ ] **Step 4: Daftarkan router di `app/main.py`**

Tambahkan setelah `from app.routers import auth`:
```python
from app.routers import webhooks
```

Dan tambahkan setelah `app.include_router(auth.router)`:
```python
app.include_router(webhooks.router)
```

- [ ] **Step 5: Tulis tests**

```python
# backend/tests/test_webhook_router.py
import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_facebook_verify_success(client):
    settings = get_settings()
    res = client.get("/webhooks/facebook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.META_VERIFY_TOKEN,
        "hub.challenge": "challenge-abc123",
    })
    assert res.status_code == 200
    assert res.text == "challenge-abc123"


def test_facebook_verify_wrong_token_returns_403(client):
    res = client.get("/webhooks/facebook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "challenge-xyz",
    })
    assert res.status_code == 403


def test_facebook_receive_comment_event(client):
    payload = {
        "object": "page",
        "entry": [{
            "id": "page-123",
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "comment_id": "cmnt-abc",
                    "message": "Harga berapa?",
                    "from": {"id": "user-1", "name": "Budi"},
                    "post_id": "post-1",
                }
            }]
        }]
    }

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 1


def test_facebook_receive_messenger_event(client):
    payload = {
        "object": "page",
        "entry": [{
            "id": "page-123",
            "messaging": [{
                "sender": {"id": "user-2"},
                "recipient": {"id": "page-123"},
                "message": {"mid": "m123", "text": "Halo kak!"},
            }]
        }]
    }

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["queued"] == 1


def test_facebook_receive_ignores_non_page_object(client):
    payload = {"object": "user", "entry": []}

    with patch("app.routers.webhooks.process_facebook_event") as mock_task:
        mock_task.delay = MagicMock()
        res = client.post(
            "/webhooks/facebook",
            params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
            json=payload,
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
    mock_task.delay.assert_not_called()


def test_facebook_receive_invalid_payload_returns_400(client):
    res = client.post(
        "/webhooks/facebook",
        params={"tenant_id": "00000000-0000-0000-0000-000000000001"},
        content=b"ini bukan json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400
```

- [ ] **Step 6: Jalankan tests**

```bash
pytest tests/test_webhook_router.py -v
```

Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/schemas/webhook.py backend/app/routers/webhooks.py backend/app/middleware/tenant_context.py backend/app/main.py backend/tests/test_webhook_router.py
git commit -m "feat: webhook router Facebook (verify + receive komentar + Messenger DM)"
```

---

## Task 9: Conversations Router (List + Human Takeover)

**Files:**
- Create: `backend/app/schemas/conversation.py`
- Create: `backend/app/routers/conversations.py`
- Modify: `backend/app/main.py` (daftarkan router)
- Create: `backend/tests/test_conversations_router.py`

**Interfaces:**
- Consumes: `Conversation` model dari Task 2, `get_db_session` dari Fase 1
- Produces:
  - `GET /api/v1/conversations` → `APIResponse[list[ConversationResponse]]` — list conversation tenant, filter opsional `is_human_takeover=true`
  - `PATCH /api/v1/conversations/{id}/takeover` → `APIResponse[ConversationResponse]` — toggle `is_human_takeover`

- [ ] **Step 1: Buat `app/schemas/conversation.py`**

```python
# backend/app/schemas/conversation.py
import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    platform: str
    channel_type: str
    message_in: str | None
    message_out: str | None
    intent: str | None
    sentiment: str | None
    is_human_takeover: bool
    escalation_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TakeoverRequest(BaseModel):
    is_human_takeover: bool
```

- [ ] **Step 2: Buat `app/routers/conversations.py`**

```python
# backend/app/routers/conversations.py
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.conversation import Conversation
from app.schemas.base import APIResponse
from app.schemas.conversation import ConversationResponse, TakeoverRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=APIResponse[list[ConversationResponse]])
async def list_conversations(
    request,
    is_human_takeover: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == uuid.UUID(tenant_id))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    if is_human_takeover is not None:
        stmt = stmt.where(Conversation.is_human_takeover == is_human_takeover)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return APIResponse(data=[ConversationResponse.model_validate(c) for c in conversations])


@router.patch("/{conversation_id}/takeover", response_model=APIResponse[ConversationResponse])
async def toggle_takeover(
    conversation_id: uuid.UUID,
    body: TakeoverRequest,
    request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan.")

    conv.is_human_takeover = body.is_human_takeover
    if not body.is_human_takeover:
        conv.escalation_reason = None

    logger.info(
        "Takeover toggled",
        extra={
            "tenant_id": tenant_id,
            "conversation_id": str(conversation_id),
            "is_human_takeover": body.is_human_takeover,
        },
    )
    return APIResponse(data=ConversationResponse.model_validate(conv))
```

- [ ] **Step 3: Daftarkan router di `app/main.py`**

Tambahkan:
```python
from app.routers import conversations
# ...
app.include_router(conversations.router)
```

- [ ] **Step 4: Tulis tests**

```python
# backend/tests/test_conversations_router.py
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def auth_headers():
    tenant_id = str(uuid.uuid4())
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "role": "tenant_user",
    })
    return {"Authorization": f"Bearer {token}"}, tenant_id


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _make_conv(tenant_id: str, is_human_takeover: bool = False) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.tenant_id = uuid.UUID(tenant_id)
    c.customer_id = uuid.uuid4()
    c.platform = "facebook"
    c.channel_type = "comment"
    c.message_in = "Harga berapa?"
    c.message_out = "Rp 150.000 kak!"
    c.intent = "tanya_info"
    c.sentiment = "neutral"
    c.is_human_takeover = is_human_takeover
    c.escalation_reason = None
    c.created_at = datetime.now(timezone.utc)
    return c


def test_list_conversations_requires_auth(client):
    res = client.get("/api/v1/conversations")
    assert res.status_code == 401


def test_list_conversations_returns_list(client, auth_headers):
    headers, tenant_id = auth_headers
    conv = _make_conv(tenant_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [conv]

    with patch("app.routers.conversations.get_db_session") as mock_db:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=False)

        # Override dependency
        app.dependency_overrides = {}

        from app.core.database import get_db_session as real_db
        async def override_db(request):
            yield mock_session
        app.dependency_overrides[real_db] = override_db

        res = client.get("/api/v1/conversations", headers=headers)
        app.dependency_overrides = {}

    assert res.status_code == 200
    assert res.json()["success"] is True


def test_toggle_takeover_not_found(client, auth_headers):
    headers, tenant_id = auth_headers
    conv_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    from app.core.database import get_db_session as real_db
    async def override_db(request):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        yield mock_session
    app.dependency_overrides[real_db] = override_db

    res = client.patch(
        f"/api/v1/conversations/{conv_id}/takeover",
        headers=headers,
        json={"is_human_takeover": False},
    )
    app.dependency_overrides = {}

    assert res.status_code == 404


def test_toggle_takeover_success(client, auth_headers):
    headers, tenant_id = auth_headers
    conv = _make_conv(tenant_id, is_human_takeover=True)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = conv

    from app.core.database import get_db_session as real_db
    async def override_db(request):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        yield mock_session
    app.dependency_overrides[real_db] = override_db

    res = client.patch(
        f"/api/v1/conversations/{conv.id}/takeover",
        headers=headers,
        json={"is_human_takeover": False},
    )
    app.dependency_overrides = {}

    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["is_human_takeover"] is False
```

- [ ] **Step 5: Jalankan tests**

```bash
pytest tests/test_conversations_router.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd /home/px/Projects/Reseller
git add backend/app/schemas/conversation.py backend/app/routers/conversations.py backend/app/main.py backend/tests/test_conversations_router.py
git commit -m "feat: conversations router (list + human takeover toggle)"
```

---

## Task 10: Full Test Suite & Smoke Test

**Files:**
- No new files

- [ ] **Step 1: Jalankan full test suite**

```bash
cd /home/px/Projects/Reseller/backend
source .venv/bin/activate
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: semua test PASSED (Fase 1 + Fase 2).

- [ ] **Step 2: Smoke test — jalankan server**

```bash
uvicorn app.main:app --reload --port 8001
```

Buka `http://localhost:8001/docs` — verifikasi endpoint baru muncul:
- `GET /webhooks/facebook`
- `POST /webhooks/facebook`
- `GET /api/v1/conversations`
- `PATCH /api/v1/conversations/{conversation_id}/takeover`

- [ ] **Step 3: Test webhook verify via curl**

```bash
# Ganti nilai META_VERIFY_TOKEN sesuai .env kamu
curl "http://localhost:8001/webhooks/facebook?hub.mode=subscribe&hub.verify_token=reseller-ai-webhook-verify-secret&hub.challenge=test123"
```

Expected: `test123`

- [ ] **Step 4: Commit final Fase 2**

```bash
cd /home/px/Projects/Reseller
git add -A
git commit -m "test: Fase 2 full test suite pass — Engagement Engine backend selesai"
```

---

## Self-Review

### Spec Coverage

| Requirement SDD v2.5 | Task |
|---|---|
| Webhook receiver Facebook (komentar + Messenger DM) | Task 8 |
| Verifikasi signature X-Hub-Signature-256 | Task 8 |
| Verifikasi token GET webhook | Task 8 |
| Intent classifier via OpenRouter | Task 3 |
| RAG service (pgvector, fase 2: keyword fallback) | Task 4 |
| Auto-reply engine | Task 6 |
| Celery engagement_worker retry + log (RULE-04) | Task 7 |
| Human takeover: kolom `is_human_takeover` | Task 2 |
| Human takeover: toggle via PATCH API | Task 9 |
| Human takeover: skip AI jika aktif | Task 6 |
| Eskalasi otomatis dari `escalation_topics` | Task 6 |
| Eskalasi otomatis: komplain + sentimen negatif | Task 6 |
| Dedup event (platform_message_id) | Task 6 |
| Log ke `system_logs` (RULE-04) | Task 6 |
| Abstraksi provider OpenRouter/OpenAI | Task 3 |
| RULE-01: feature flag sebelum eksekusi | Task 6, 7 |
| RULE-03: tenant_id filter di semua query | Task 6, 9 |
| Model `Customer` + `Conversation` + migration | Task 2 |
| Model `Product` (untuk RAG fallback) | Task 4 |
| Config env vars baru (OPENROUTER, META_VERIFY_TOKEN) | Task 1 |
| `GET /api/v1/conversations` dengan filter | Task 9 |
| `PATCH /api/v1/conversations/{id}/takeover` | Task 9 |
| Fallback reply jika AI error | Task 3 |
| Fallback pesan ke customer jika ada masalah teknis (SDD 16.5) | Task 3 (`FALLBACK_REPLY`) |
