# Instagram Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambah backend endpoint + frontend UI untuk tenant connect Instagram Business Account mereka lewat halaman Settings.

**Architecture:** Mirror pola Facebook settings yang sudah ada. Backend: tambah schema, service function, dan endpoint. Frontend: update hook type + tambah card Instagram di Settings page. Tidak ada OAuth — user input token manual.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest (backend) · React 19, TypeScript, Zustand, Axios (frontend)

## Global Constraints

- Platform string DB: `"instagram"` (lowercase, konsisten dengan engagement service)
- Field request: `page_token` (min 10 char) + `instagram_account_id` (min 1 char)
- Endpoint prefix: `/api/v1/settings/`
- Ikuti pola test yang ada: `unittest.mock`, `pytest.mark.asyncio`, patch by dotted path
- Tidak ada perubahan pada kode Facebook yang sudah ada
- Tidak ada validasi token ke Meta API — simpan as-is

---

## File Map

| File | Action | Tanggung jawab |
|---|---|---|
| `backend/app/schemas/settings.py` | **Edit** | Tambah `SaveIGTokenRequest`, update `SettingsResponse` |
| `backend/app/services/settings_service.py` | **Edit** | Tambah `save_ig_token`, update `get_settings_status` |
| `backend/app/routers/settings.py` | **Edit** | Tambah `POST /api/v1/settings/instagram-token` |
| `backend/tests/test_settings_service.py` | **Edit** | Test untuk `save_ig_token` + update `get_settings_status` |
| `backend/tests/test_settings_router.py` | **Create** | Test endpoint instagram-token |
| `frontend/src/hooks/useSettings.ts` | **Edit** | Update type + tambah `saveIGToken` |
| `frontend/src/pages/Settings.tsx` | **Edit** | Tambah card Instagram |

---

## Task 1: Backend — Schema, Service, Endpoint

**Files:**
- Modify: `backend/app/schemas/settings.py`
- Modify: `backend/app/services/settings_service.py`
- Modify: `backend/app/routers/settings.py`
- Test: `backend/tests/test_settings_service.py`
- Create: `backend/tests/test_settings_router.py`

**Interfaces:**
- Produces:
  - `SaveIGTokenRequest` — Pydantic model dengan field `page_token: str`, `instagram_account_id: str`
  - `SettingsResponse` — update dengan field `instagram_connected: bool`
  - `save_ig_token(tenant_id: str, page_token: str, account_id: str, db: AsyncSession) -> TenantCredential`
  - `GET /api/v1/settings` — sekarang returns `instagram_connected` juga
  - `POST /api/v1/settings/instagram-token` — simpan token Instagram

- [ ] **Step 1: Tulis failing tests untuk `save_ig_token` dan `get_settings_status` update**

Tambahkan ke `backend/tests/test_settings_service.py` — append setelah isi yang ada:

```python
from app.services.settings_service import get_settings_status, save_fb_token, save_ig_token


@pytest.mark.asyncio
async def test_get_settings_status_includes_instagram_connected():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    # fb cred query
    fb_cred_result = MagicMock()
    fb_cred_result.scalar_one_or_none.return_value = None
    # ig cred query
    ig_cred = MagicMock()
    ig_cred.is_expired.return_value = False
    ig_cred_result = MagicMock()
    ig_cred_result.scalar_one_or_none.return_value = ig_cred
    # product count query
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    db.execute.side_effect = [fb_cred_result, ig_cred_result, count_result]

    status = await get_settings_status(tenant_id, db)
    assert status["instagram_connected"] is True
    assert status["facebook_connected"] is False
    assert status["product_count"] == 2


@pytest.mark.asyncio
async def test_save_ig_token_creates_new():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.return_value = existing_result

    with patch("app.services.settings_service.encrypt_credential", return_value="encrypted_ig"):
        result = await save_ig_token(tenant_id, "ig_raw_token_xyz", "ig_account_id_123", db)

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_ig_token_updates_existing():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    existing_cred = MagicMock()
    existing_cred.access_token_encrypted = "old_encrypted_ig"
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_cred
    db.execute.return_value = existing_result

    with patch("app.services.settings_service.encrypt_credential", return_value="new_encrypted_ig"):
        result = await save_ig_token(tenant_id, "new_ig_token", "ig_account_id_123", db)

    assert result.access_token_encrypted == "new_encrypted_ig"
    db.add.assert_not_called()
```

- [ ] **Step 2: Jalankan test — verifikasi FAIL**

```bash
cd backend && python3 -m pytest tests/test_settings_service.py::test_save_ig_token_creates_new -v 2>/dev/null | grep "FAIL\|PASS\|Error"
```

Expected: `ImportError: cannot import name 'save_ig_token'`

- [ ] **Step 3: Update `schemas/settings.py`**

Isi penuh file setelah edit:

```python
from pydantic import BaseModel, Field


class SaveFBTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    page_id: str = Field(..., min_length=1)


class SaveIGTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    instagram_account_id: str = Field(..., min_length=1)


class SettingsResponse(BaseModel):
    facebook_connected: bool
    instagram_connected: bool
    product_count: int
```

- [ ] **Step 4: Update `services/settings_service.py`**

Isi penuh file setelah edit:

```python
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_credential
from app.models.product import Product
from app.models.tenant_credential import TenantCredential

logger = logging.getLogger(__name__)


async def get_settings_status(tenant_id: str, db: AsyncSession) -> dict:
    fb_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    fb_cred = fb_result.scalar_one_or_none()
    facebook_connected = fb_cred is not None and not fb_cred.is_expired()

    ig_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    ig_cred = ig_result.scalar_one_or_none()
    instagram_connected = ig_cred is not None and not ig_cred.is_expired()

    count_result = await db.execute(
        select(func.count()).select_from(Product).where(
            Product.tenant_id == uuid.UUID(tenant_id),
            Product.status == "active",
        )
    )
    product_count = count_result.scalar() or 0

    return {
        "facebook_connected": facebook_connected,
        "instagram_connected": instagram_connected,
        "product_count": product_count,
    }


async def save_fb_token(
    tenant_id: str, page_token: str, page_id: str, db: AsyncSession
) -> TenantCredential:
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="facebook",
            access_token_encrypted=encrypted,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted

    await db.flush()
    logger.info("FB token saved", extra={"tenant_id": tenant_id, "page_id": page_id})
    return credential


async def save_ig_token(
    tenant_id: str, page_token: str, account_id: str, db: AsyncSession
) -> TenantCredential:
    existing_result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
        )
    )
    credential = existing_result.scalar_one_or_none()
    encrypted = encrypt_credential(page_token)

    if credential is None:
        credential = TenantCredential(
            tenant_id=uuid.UUID(tenant_id),
            platform="instagram",
            access_token_encrypted=encrypted,
        )
        db.add(credential)
    else:
        credential.access_token_encrypted = encrypted

    await db.flush()
    logger.info("IG token saved", extra={"tenant_id": tenant_id, "account_id": account_id})
    return credential
```

- [ ] **Step 5: Update `routers/settings.py`**

Isi penuh file setelah edit:

```python
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse
from app.schemas.settings import SaveFBTokenRequest, SaveIGTokenRequest, SettingsResponse
from app.services.settings_service import get_settings_status, save_fb_token, save_ig_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=APIResponse[SettingsResponse])
async def get_settings_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    status = await get_settings_status(tenant_id, db)
    return APIResponse(data=SettingsResponse(**status))


@router.post("/facebook-token", response_model=APIResponse[None])
async def save_facebook_token(
    body: SaveFBTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    await save_fb_token(tenant_id, body.page_token, body.page_id, db)
    return APIResponse(data=None, message="Facebook Page token berhasil disimpan.")


@router.post("/instagram-token", response_model=APIResponse[None])
async def save_instagram_token(
    body: SaveIGTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id
    await save_ig_token(tenant_id, body.page_token, body.instagram_account_id, db)
    return APIResponse(data=None, message="Instagram token berhasil disimpan.")
```

- [ ] **Step 6: Tulis test untuk endpoint instagram-token**

Buat `backend/tests/test_settings_router.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def auth_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/api/v1/auth/register", json={
            "name": "Settings Test",
            "email": "settingstest_ig@test.com",
            "password": "Test1234!",
        })
        c.post("/api/v1/auth/login", json={
            "email": "settingstest_ig@test.com",
            "password": "Test1234!",
        })
        yield c


def test_instagram_token_endpoint_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        res = c.post("/api/v1/settings/instagram-token", json={
            "page_token": "EAAxxxxxxxxxxxxxxx",
            "instagram_account_id": "123456789",
        })
    assert res.status_code == 401


def test_instagram_token_endpoint_saves_token(auth_client):
    with patch("app.routers.settings.save_ig_token", new_callable=AsyncMock) as mock_save:
        res = auth_client.post("/api/v1/settings/instagram-token", json={
            "page_token": "EAAxxxxxxxxxxxxxxx",
            "instagram_account_id": "123456789",
        })

    assert res.status_code == 200
    assert res.json()["message"] == "Instagram token berhasil disimpan."
    mock_save.assert_called_once()


def test_instagram_token_endpoint_rejects_short_token(auth_client):
    res = auth_client.post("/api/v1/settings/instagram-token", json={
        "page_token": "short",
        "instagram_account_id": "123456789",
    })
    assert res.status_code == 422


def test_instagram_token_endpoint_rejects_missing_account_id(auth_client):
    res = auth_client.post("/api/v1/settings/instagram-token", json={
        "page_token": "EAAxxxxxxxxxxxxxxx",
    })
    assert res.status_code == 422
```

- [ ] **Step 7: Jalankan semua test backend — verifikasi PASS**

```bash
cd backend && python3 -m pytest tests/test_settings_service.py tests/test_settings_router.py -v 2>/dev/null | grep "FAIL\|PASS\|pass\|fail"
```

Expected: Semua pass. Test lama `test_get_settings_status_*` perlu diperhatikan — `db.execute.side_effect` sekarang butuh 3 return values (fb, ig, count). Jika ada yang fail karena ini, update test lama:

Untuk `test_get_settings_status_no_credential` — update `db.execute.side_effect`:
```python
ig_cred_result = MagicMock()
ig_cred_result.scalar_one_or_none.return_value = None
db.execute.side_effect = [cred_result, ig_cred_result, count_result]
```

Untuk `test_get_settings_status_with_credential` — update `db.execute.side_effect`:
```python
ig_cred_result = MagicMock()
ig_cred_result.scalar_one_or_none.return_value = None
db.execute.side_effect = [cred_result, ig_cred_result, count_result]
```

- [ ] **Step 8: Commit**

```bash
cd backend && git add app/schemas/settings.py app/services/settings_service.py app/routers/settings.py tests/test_settings_service.py tests/test_settings_router.py
git commit -m "feat: add Instagram settings endpoint and save_ig_token service"
```

---

## Task 2: Frontend — Hook + Settings UI

**Files:**
- Modify: `frontend/src/hooks/useSettings.ts`
- Modify: `frontend/src/pages/Settings.tsx`

**Interfaces:**
- Consumes: `POST /api/v1/settings/instagram-token` dengan body `{page_token, instagram_account_id}` (Task 1)
- Consumes: `GET /api/v1/settings` yang sekarang returns `instagram_connected: boolean` (Task 1)

- [ ] **Step 1: Update `frontend/src/hooks/useSettings.ts`**

Isi penuh file setelah edit:

```typescript
import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface SettingsStatus {
  facebook_connected: boolean;
  instagram_connected: boolean;
  product_count: number;
}

export function useSettings() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: SettingsStatus }>("/settings");
      setStatus(res.data.data);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  async function saveFBToken(pageToken: string, pageId: string): Promise<void> {
    await api.post("/settings/facebook-token", { page_token: pageToken, page_id: pageId });
    await fetchStatus();
  }

  async function saveIGToken(pageToken: string, accountId: string): Promise<void> {
    await api.post("/settings/instagram-token", { page_token: pageToken, instagram_account_id: accountId });
    await fetchStatus();
  }

  return { status, isLoading, saveFBToken, saveIGToken };
}
```

- [ ] **Step 2: Update `frontend/src/pages/Settings.tsx`**

Isi penuh file setelah edit:

```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/useSettings";
import AppLayout from "@/components/AppLayout";

export default function Settings() {
  const { status, isLoading, saveFBToken, saveIGToken } = useSettings();

  const [pageToken, setPageToken] = useState("");
  const [pageId, setPageId] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [igPageToken, setIgPageToken] = useState("");
  const [igAccountId, setIgAccountId] = useState("");
  const [igSaving, setIgSaving] = useState(false);
  const [igSaveError, setIgSaveError] = useState<string | null>(null);
  const [igSaveSuccess, setIgSaveSuccess] = useState(false);

  async function handleSaveFB(e: React.FormEvent) {
    e.preventDefault();
    if (!pageToken.trim() || !pageId.trim()) {
      setSaveError("Page Token dan Page ID wajib diisi.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await saveFBToken(pageToken.trim(), pageId.trim());
      setPageToken("");
      setPageId("");
      setSaveSuccess(true);
    } catch {
      setSaveError("Gagal menyimpan token. Pastikan token valid.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveIG(e: React.FormEvent) {
    e.preventDefault();
    if (!igPageToken.trim() || !igAccountId.trim()) {
      setIgSaveError("Page Token dan Instagram Account ID wajib diisi.");
      return;
    }
    setIgSaving(true);
    setIgSaveError(null);
    setIgSaveSuccess(false);
    try {
      await saveIGToken(igPageToken.trim(), igAccountId.trim());
      setIgPageToken("");
      setIgAccountId("");
      setIgSaveSuccess(true);
    } catch {
      setIgSaveError("Gagal menyimpan token. Pastikan token valid.");
    } finally {
      setIgSaving(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6 space-y-6">
        <h1 className="text-xl font-semibold text-slate-900">Pengaturan</h1>

        {/* Facebook Card */}
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium text-slate-800">Facebook Page</h2>
            {!isLoading && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  status?.facebook_connected
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {status?.facebook_connected ? "Terhubung" : "Belum terhubung"}
              </span>
            )}
          </div>

          <p className="mb-4 text-sm text-slate-500">
            Masukkan Facebook Page Access Token untuk mengaktifkan auto-reply komentar dan Messenger
            DM. Generate token di{" "}
            <a
              href="https://developers.facebook.com/tools/explorer"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Graph API Explorer
            </a>{" "}
            dengan permission{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">pages_manage_engagement</code>.
          </p>

          <form onSubmit={handleSaveFB} className="space-y-3">
            <div>
              <Label htmlFor="pageId">Page ID</Label>
              <Input
                id="pageId"
                value={pageId}
                onChange={(e) => setPageId(e.target.value)}
                placeholder="1234567890"
              />
            </div>
            <div>
              <Label htmlFor="pageToken">Page Access Token</Label>
              <Input
                id="pageToken"
                type="password"
                value={pageToken}
                onChange={(e) => setPageToken(e.target.value)}
                placeholder="EAAxxxx..."
              />
            </div>
            {saveError && <p className="text-sm text-red-600">{saveError}</p>}
            {saveSuccess && (
              <p className="text-sm text-green-600">Token berhasil disimpan. AI aktif.</p>
            )}
            <Button type="submit" disabled={saving} size="sm">
              {saving ? "Menyimpan..." : "Simpan Token"}
            </Button>
          </form>
        </div>

        {/* Instagram Card */}
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium text-slate-800">Instagram Business</h2>
            {!isLoading && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  status?.instagram_connected
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {status?.instagram_connected ? "Terhubung" : "Belum terhubung"}
              </span>
            )}
          </div>

          <p className="mb-4 text-sm text-slate-500">
            Masukkan Page Access Token dari Facebook Page yang terhubung ke akun Instagram Business
            kamu. Generate token di{" "}
            <a
              href="https://developers.facebook.com/tools/explorer"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Graph API Explorer
            </a>{" "}
            dengan permission{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">instagram_basic</code>{" "}
            dan{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">instagram_manage_messages</code>.
          </p>

          <form onSubmit={handleSaveIG} className="space-y-3">
            <div>
              <Label htmlFor="igAccountId">Instagram Account ID</Label>
              <Input
                id="igAccountId"
                value={igAccountId}
                onChange={(e) => setIgAccountId(e.target.value)}
                placeholder="17841400000000000"
              />
            </div>
            <div>
              <Label htmlFor="igPageToken">Page Access Token</Label>
              <Input
                id="igPageToken"
                type="password"
                value={igPageToken}
                onChange={(e) => setIgPageToken(e.target.value)}
                placeholder="EAAxxxx..."
              />
            </div>
            {igSaveError && <p className="text-sm text-red-600">{igSaveError}</p>}
            {igSaveSuccess && (
              <p className="text-sm text-green-600">Token berhasil disimpan. AI aktif.</p>
            )}
            <Button type="submit" disabled={igSaving} size="sm">
              {igSaving ? "Menyimpan..." : "Simpan Token"}
            </Button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 3: Verifikasi TypeScript compile**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: Build berhasil tanpa error TypeScript.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/hooks/useSettings.ts src/pages/Settings.tsx
git commit -m "feat: add Instagram settings card and saveIGToken hook"
```

---

## Self-Review

**Spec coverage:**
- ✓ `SaveIGTokenRequest` dengan `page_token` + `instagram_account_id` — Task 1
- ✓ `SettingsResponse` update dengan `instagram_connected` — Task 1
- ✓ `save_ig_token()` upsert TenantCredential platform="instagram" — Task 1
- ✓ `get_settings_status()` cek credential instagram — Task 1
- ✓ `POST /api/v1/settings/instagram-token` — Task 1
- ✓ `saveIGToken()` di hook — Task 2
- ✓ Card Instagram di Settings page dengan badge status — Task 2
- ✓ Form: Instagram Account ID + Page Access Token — Task 2
- ✓ Error + success feedback — Task 2
- ✓ Link ke Graph API Explorer dengan permission yang benar — Task 2

**Type consistency:**
- `saveIGToken(pageToken: string, accountId: string)` — konsisten hook → Settings.tsx
- `save_ig_token(tenant_id, page_token, account_id, db)` — konsisten service → router
- `instagram_connected: bool` — konsisten service dict → SettingsResponse → hook type

**Placeholders:** Tidak ada.

**Note untuk implementer:** Test lama `test_get_settings_status_no_credential` dan `test_get_settings_status_with_credential` di `test_settings_service.py` perlu di-update karena `get_settings_status` sekarang melakukan 3 query (fb, ig, count) bukan 2. Step 7 Task 1 sudah menjelaskan fix-nya.
