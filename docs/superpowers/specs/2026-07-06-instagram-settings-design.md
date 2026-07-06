# Instagram Settings — Design Spec

**Date:** 2026-07-06
**Scope:** Backend endpoint + frontend UI untuk connect Instagram Business Account
**Approach:** Mirror pola Facebook settings yang sudah ada

---

## Overview

Tambah kemampuan tenant untuk connect akun Instagram Business mereka lewat panel Settings. Mengikuti pola `save_fb_token` / Facebook card yang sudah ada. Credential disimpan terpisah sebagai platform `"instagram"` — boleh pakai token yang sama dengan Facebook.

---

## Data yang Diinput User

| Field | Keterangan |
|---|---|
| `instagram_account_id` | Instagram Business Account ID (IGSID, bukan username) |
| `page_token` | Page Access Token dari Facebook Page yang linked ke Instagram Business Account |

Token di-generate di [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer) dengan permission `instagram_basic` dan `instagram_manage_messages`.

---

## Architecture

```
Frontend Settings page
    ↓ POST /api/v1/settings/instagram-token {page_token, instagram_account_id}
Backend router → save_ig_token(tenant_id, page_token, account_id, db)
    ↓ upsert TenantCredential(platform="instagram", access_token_encrypted=encrypt(page_token))
    ↓ return 200

Frontend GET /api/v1/settings
    ↓ SettingsResponse {facebook_connected, instagram_connected, product_count}
```

---

## Components

### 1. `backend/app/schemas/settings.py`

Tambah:
```python
class SaveIGTokenRequest(BaseModel):
    page_token: str = Field(..., min_length=10)
    instagram_account_id: str = Field(..., min_length=1)
```

Update `SettingsResponse`:
```python
class SettingsResponse(BaseModel):
    facebook_connected: bool
    instagram_connected: bool
    product_count: int
```

### 2. `backend/app/services/settings_service.py`

Update `get_settings_status()` — tambah cek credential `"instagram"`:
```python
instagram_connected = <credential platform="instagram"> is not None and not expired
return {"facebook_connected": ..., "instagram_connected": instagram_connected, "product_count": ...}
```

Tambah `save_ig_token(tenant_id, page_token, account_id, db)`:
- Identik dengan `save_fb_token()` tapi platform `"instagram"`
- Upsert `TenantCredential` — update jika sudah ada, insert jika belum
- Encrypt token sebelum disimpan

### 3. `backend/app/routers/settings.py`

Tambah endpoint:
```
POST /api/v1/settings/instagram-token
Body: SaveIGTokenRequest
Response: APIResponse[None], message "Instagram token berhasil disimpan."
```

### 4. `frontend/src/hooks/useSettings.ts`

Update `SettingsStatus`:
```typescript
interface SettingsStatus {
  facebook_connected: boolean;
  instagram_connected: boolean;
  product_count: number;
}
```

Tambah fungsi:
```typescript
async function saveIGToken(pageToken: string, accountId: string): Promise<void>
```

### 5. `frontend/src/pages/Settings.tsx`

Tambah card Instagram di bawah card Facebook. Struktur identik dengan card Facebook:
- Header "Instagram Business" + badge status (Terhubung / Belum terhubung)
- Deskripsi singkat + link Graph API Explorer dengan permission yang diperlukan
- Form: field `Instagram Account ID` + field `Page Access Token` (type password)
- Tombol "Simpan Token"
- Feedback: error message + success message

---

## Error Handling

| Kondisi | Handling |
|---|---|
| Field kosong | Frontend validation — tampilkan error sebelum submit |
| API error | Catch exception, tampilkan "Gagal menyimpan token." |
| Token sudah ada | Upsert — overwrite dengan token baru |

---

## Files Changed

| File | Action |
|---|---|
| `backend/app/schemas/settings.py` | Edit — tambah `SaveIGTokenRequest`, update `SettingsResponse` |
| `backend/app/services/settings_service.py` | Edit — tambah `save_ig_token`, update `get_settings_status` |
| `backend/app/routers/settings.py` | Edit — tambah endpoint POST instagram-token |
| `frontend/src/hooks/useSettings.ts` | Edit — update type + tambah `saveIGToken` |
| `frontend/src/pages/Settings.tsx` | Edit — tambah card Instagram |

---

## Out of Scope

- OAuth flow untuk Instagram
- Validasi token ke Meta API saat save
- Disconnect / hapus token
