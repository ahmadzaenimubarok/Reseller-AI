# Frontend Fase 2 — Login + Inbox Dashboard

**Date:** 2026-07-04
**Scope:** Fase 2 frontend minimum — auth (JWT httpOnly cookie) + Inbox page (percakapan + human takeover toggle)

---

## 1. Stack

| Layer | Pilihan |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand |
| HTTP | Axios (`withCredentials: true`) |
| Routing | React Router v6 |

---

## 2. Struktur File

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx              ← router setup, protected route wrapper
│   ├── pages/
│   │   ├── Login.tsx        ← form login, redirect ke /inbox setelah sukses
│   │   └── Inbox.tsx        ← list percakapan + toggle takeover
│   ├── components/
│   │   ├── FeatureGate.tsx  ← RULE-07: wrap fitur yang butuh integrasi eksternal
│   │   └── ui/              ← shadcn/ui components (button, table, badge, alert, dll)
│   ├── hooks/
│   │   ├── useAuth.ts           ← cek sesi aktif, expose logout()
│   │   ├── useFeatureStatus.ts  ← fetch status fitur dari backend
│   │   └── useConversations.ts  ← fetch list + toggle takeover, polling 10 detik
│   └── lib/
│       └── api.ts           ← Axios instance, interceptor 401 → redirect /login
```

---

## 3. Auth — Backend Changes (Plan A)

### 3.1 Endpoints yang dimodifikasi

**`POST /api/v1/auth/login`**
- Response: set 2 httpOnly cookie (`access_token`, `refresh_token`), body hanya return `{token_type: "bearer"}`
- Cookie flags: `HttpOnly=True`, `SameSite=Lax`, `Secure=True` (production), `Path=/`
- `access_token` max_age: sesuai `ACCESS_TOKEN_EXPIRE_MINUTES` di config
- `refresh_token` max_age: sesuai `REFRESH_TOKEN_EXPIRE_DAYS` di config

**`POST /api/v1/auth/refresh`**
- Baca `refresh_token` dari cookie (bukan body)
- Set cookie baru seperti login

**`POST /api/v1/auth/logout`** (endpoint baru)
- Clear kedua cookie (set max_age=0)
- Return `{message: "Logout berhasil"}`

**`GET /api/v1/auth/me`** (endpoint baru)
- Baca JWT dari cookie, return user info: `{user_id, tenant_id, role}`
- Dipakai frontend untuk cek sesi aktif

### 3.2 CORS update

```python
allow_origins=["http://localhost:5173", "https://dashboard.jawakoentji.my.id"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

### 3.3 Middleware update

Backend sudah punya middleware yang set `request.state.tenant_id`. Update: baca JWT dari cookie `access_token`, bukan `Authorization` header. Header tetap didukung sebagai fallback (untuk Postman/testing).

---

## 4. Auth — Frontend Flow

1. User buka `/` → redirect ke `/login` (belum ada cookie)
2. Submit login form → `POST /auth/login` → browser simpan cookie otomatis
3. Redirect ke `/inbox`
4. `useAuth` hook panggil `GET /auth/me` untuk validasi sesi — jika 401, redirect `/login`
5. Axios interceptor tangkap semua 401 → redirect `/login`
6. Logout → `POST /auth/logout` → cookie cleared → redirect `/login`

`tenant_id` tidak disimpan di frontend state — backend decode dari JWT cookie di setiap request.

---

## 5. Feature Status Endpoint (backend baru)

**`GET /api/v1/features/{feature_name}`**
- Auth required (baca tenant_id dari JWT)
- Return: `{status: "active" | "not_configured" | "expired" | "plan_locked" | "quota_exceeded"}`
- Dipakai `useFeatureStatus` hook di frontend

Contoh: `GET /api/v1/features/facebook_engagement`

---

## 6. Inbox Page

### 6.1 Layout

Seluruh konten dibungkus `<FeatureGate feature="facebook_engagement">` (RULE-07).

Tampilan: tabel dengan kolom:
| Kolom | Source |
|---|---|
| Platform | `conversation.platform` |
| Pesan masuk | `conversation.message_in` (truncate 80 char) |
| Intent | `conversation.intent` (badge) |
| Sentiment | `conversation.sentiment` (badge warna) |
| Status | `is_human_takeover` → badge "Human" / "AI" |
| Waktu | `conversation.created_at` (format relatif) |
| Aksi | Toggle switch takeover |

### 6.2 Filter

Dropdown/tab di atas tabel: **Semua** / **AI** / **Human** — mengatur query param `is_human_takeover`.

### 6.3 Data Fetching

- `useConversations` hook — polling setiap 10 detik dengan `setInterval`
- Query: `GET /api/v1/conversations?limit=50` (+ optional `is_human_takeover` filter)
- Toggle takeover: `PATCH /api/v1/conversations/{id}/takeover` body `{is_human_takeover: bool}` → optimistic update, revert jika error

### 6.4 State

```ts
// Zustand store (minimal)
{
  conversations: ConversationResponse[]
  filter: "all" | "ai" | "human"
  setFilter: (f) => void
  setConversations: (c[]) => void
}
```

---

## 7. FeatureGate Component

Sesuai spec SDD §14.6. Status yang ditangani:
- `not_configured` → alert "Belum terhubung" + link ke Settings
- `expired` → alert "Koneksi kedaluwarsa" + link reconnect
- `plan_locked` → alert "Tersedia di plan lebih tinggi" + link Billing
- `quota_exceeded` → alert "Kuota habis" + link Billing
- `active` → render children
- loading → skeleton pulse

---

## 8. Error Handling

- Axios interceptor (sesuai RULE di SDD): tangkap semua error response, normalize ke format `{message, code}`
- 401 → redirect `/login`
- 403 → toast "Akses ditolak"
- 422/400 → tampilkan pesan dari response body
- 5xx → toast "Terjadi kesalahan server"

---

## 9. Yang Tidak Dikerjakan di Fase Ini

- Halaman selain Login + Inbox
- WebSocket (Fase 4)
- Register flow UI (backend sudah ada, UI belum perlu)
- Mobile responsiveness (nice to have, bukan blocker)
