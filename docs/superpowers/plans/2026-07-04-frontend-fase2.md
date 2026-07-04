# Frontend Fase 2 — Login + Inbox Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bangun frontend React minimal Fase 2 — Login page + Inbox page (list percakapan + human takeover toggle) dengan auth JWT via httpOnly cookie.

**Architecture:** Backend dimodifikasi untuk set JWT sebagai httpOnly cookie (bukan JSON body). Frontend React + Vite SPA dengan Zustand untuk state, Axios dengan `withCredentials: true`, polling 10 detik untuk Inbox. FeatureGate component (RULE-07) membungkus semua fitur yang bergantung integrasi eksternal.

**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Zustand, Axios, React Router v6, python-jose (backend sudah pakai), Impeccable (slop detector)

## Global Constraints

- Semua fitur UI yang bergantung integrasi eksternal wajib dibungkus `<FeatureGate>` (RULE-07)
- Axios instance selalu `withCredentials: true`
- Semua 401 response → redirect `/login`
- `tenant_id` tidak pernah disimpan di frontend state — backend decode dari JWT cookie
- Setiap task wajib lolos `npx impeccable detect src/` sebelum commit
- No gradient-text, no ghost-cards, no over-rounding, no ai-color-palette (Impeccable rules)
- Backend CORS: `allow_credentials=True`, origins spesifik (bukan `*`)
- Cookie flags: `HttpOnly=True`, `SameSite=Lax`, `Secure` hanya production

---

## File Map

### Backend (modified)
- `backend/app/routers/auth.py` — tambah `/logout`, `/me`; modifikasi `/login` dan `/refresh` untuk set cookie
- `backend/app/routers/features.py` — **baru**: endpoint `GET /api/v1/features/{feature_name}`
- `backend/app/middleware/tenant_context.py` — baca token dari cookie sebagai primary, header sebagai fallback
- `backend/app/main.py` — tambah CORSMiddleware, include `features` router
- `backend/app/schemas/auth.py` — tambah `MeResponse`, modifikasi `TokenResponse`
- `backend/tests/test_auth.py` — tambah test untuk `/logout` dan `/me`
- `backend/tests/test_features_router.py` — **baru**: test feature status endpoint

### Frontend (semua baru)
- `frontend/package.json` — dependencies
- `frontend/vite.config.ts` — Vite config + proxy ke backend
- `frontend/tailwind.config.ts` — Tailwind config
- `frontend/tsconfig.json` — TypeScript config
- `frontend/PRODUCT.md` — Impeccable brand context
- `frontend/src/main.tsx` — entry point
- `frontend/src/App.tsx` — router + ProtectedRoute wrapper
- `frontend/src/lib/api.ts` — Axios instance + interceptor
- `frontend/src/hooks/useAuth.ts` — cek sesi via `/auth/me`, expose `logout()`
- `frontend/src/hooks/useFeatureStatus.ts` — fetch status fitur dari backend
- `frontend/src/hooks/useConversations.ts` — fetch + polling + toggle takeover
- `frontend/src/store/inbox.ts` — Zustand store untuk conversations
- `frontend/src/pages/Login.tsx` — form login
- `frontend/src/pages/Inbox.tsx` — tabel percakapan + filter + toggle
- `frontend/src/components/FeatureGate.tsx` — gate component (RULE-07)
- `frontend/src/components/ui/` — shadcn/ui components (via CLI)

---

## Task 1: Backend — Modifikasi Auth Endpoint (Cookie)

**Files:**
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Produces:
  - `POST /api/v1/auth/login` → set cookie `access_token` + `refresh_token`, return `{"token_type": "bearer"}`
  - `POST /api/v1/auth/refresh` → baca cookie `refresh_token`, set cookie baru
  - `POST /api/v1/auth/logout` → clear kedua cookie, return `{"message": "Logout berhasil"}`
  - `GET /api/v1/auth/me` → return `{"user_id": str, "tenant_id": str, "role": str}`

- [ ] **Step 1: Tambah `MeResponse` schema dan modifikasi `TokenResponse`**

Edit `backend/app/schemas/auth.py`:
```python
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
    token_type: str = "bearer"

class MeResponse(BaseModel):
    user_id: str
    tenant_id: str
    role: str
```

- [ ] **Step 2: Modifikasi auth router — set cookie, tambah `/logout` dan `/me`**

Timpa seluruh `backend/app/routers/auth.py`:
```python
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.auth import LoginRequest, MeResponse, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.base import APIResponse
from app.schemas.tenant import TenantResponse
from app.services.auth_service import login_user, refresh_access_token, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    is_prod = settings.ENV == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


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


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    tokens = await login_user(body, db)
    response = JSONResponse(
        content={"success": True, "data": {"token_type": "bearer"}, "message": None, "code": None}
    )
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return response


@router.post("/refresh")
async def refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan.")
    tokens = await refresh_access_token(refresh_token, None)  # db not needed for token ops
    response = JSONResponse(
        content={"success": True, "data": {"token_type": "bearer"}, "message": None, "code": None}
    )
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(
        content={"success": True, "data": None, "message": "Logout berhasil.", "code": None}
    )
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response


@router.get("/me", response_model=APIResponse[MeResponse])
async def me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan.")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid.")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Tipe token tidak valid.")
    return APIResponse(data=MeResponse(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload.get("role", "tenant_user"),
    ))
```

> **Note:** `refresh_access_token` di `auth_service.py` saat ini menerima `(refresh_token, db)` — cek apakah `db` digunakan. Jika tidak, pass `None` aman. Jika ya, inject `db: AsyncSession = Depends(get_db_session)` di parameter endpoint refresh.

- [ ] **Step 3: Cek apakah `refresh_access_token` butuh `db`**

```bash
grep -A 20 "async def refresh_access_token" backend/app/services/auth_service.py
```

Jika butuh `db`, update parameter endpoint `/refresh`:
```python
@router.post("/refresh")
async def refresh(request: Request, db: AsyncSession = Depends(get_db_session)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan.")
    tokens = await refresh_access_token(refresh_token, db)
    ...
```

- [ ] **Step 4: Tambah test untuk `/logout` dan `/me`**

Append ke `backend/tests/test_auth.py`:
```python
def test_logout_clears_cookies(client):
    # Login dulu untuk dapat cookie
    client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    # Cookie harus di-clear (max_age=0 atau tidak ada)
    assert "access_token" not in response.cookies or response.cookies["access_token"] == ""


def test_me_returns_user_info(client, test_user_token):
    # test_user_token adalah fixture yang set cookie access_token
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "user_id" in data
    assert "tenant_id" in data
    assert data["role"] == "tenant_user"


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
```

- [ ] **Step 5: Jalankan test auth**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: semua test PASS. Jika ada `test_login_returns_tokens` yang cek `access_token` di JSON body — update test tersebut: sekarang cek cookie, bukan body.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/auth.py backend/app/schemas/auth.py backend/tests/test_auth.py
git commit -m "feat: auth endpoints set JWT via httpOnly cookie (logout + me)"
```

---

## Task 2: Backend — Middleware Baca Cookie + CORS

**Files:**
- Modify: `backend/app/middleware/tenant_context.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_middleware.py`

**Interfaces:**
- Consumes: Cookie `access_token` dari request
- Produces: `request.state.tenant_id`, `request.state.user_id`, `request.state.role` (seperti sebelumnya)

- [ ] **Step 1: Update `TenantContextMiddleware` — baca cookie sebagai primary, header sebagai fallback**

Timpa method `_extract_token` di `backend/app/middleware/tenant_context.py`:
```python
def _extract_token(self, request: Request) -> str | None:
    # Cookie sebagai primary (browser)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    # Header sebagai fallback (Postman/testing)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None
```

- [ ] **Step 2: Tambah `ENV` ke config jika belum ada**

```bash
grep "ENV" backend/app/core/config.py
```

Jika tidak ada, tambah ke class `Settings`:
```python
ENV: str = "development"  # "production" untuk prod
```

- [ ] **Step 3: Tambah CORSMiddleware di `main.py`**

Edit `backend/app/main.py` — tambah import dan middleware:
```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

# Setelah `app = FastAPI(...)`:
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://dashboard.jawakoentji.my.id"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> CORSMiddleware harus ditambahkan **sebelum** middleware lain (ditambah terakhir di kode = dieksekusi pertama karena Starlette reverse-order). Tambahkan setelah `RateLimiterMiddleware` dan `TenantContextMiddleware`.

- [ ] **Step 4: Tambah test middleware untuk cookie path**

Tambah ke `backend/tests/test_middleware.py`:
```python
def test_middleware_reads_token_from_cookie(client, valid_access_token):
    response = client.get(
        "/api/v1/conversations",
        cookies={"access_token": valid_access_token},
    )
    # Tidak 401 — token dibaca dari cookie
    assert response.status_code != 401


def test_middleware_reads_token_from_header_fallback(client, valid_access_token):
    response = client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {valid_access_token}"},
    )
    assert response.status_code != 401
```

- [ ] **Step 5: Jalankan test middleware**

```bash
cd backend && python -m pytest tests/test_middleware.py -v
```

Expected: semua PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/tenant_context.py backend/app/main.py backend/tests/test_middleware.py
git commit -m "feat: middleware baca JWT dari cookie, tambah CORS"
```

---

## Task 3: Backend — Feature Status Endpoint

**Files:**
- Create: `backend/app/routers/features.py`
- Create: `backend/tests/test_features_router.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `GET /api/v1/features/{feature_name}` → `{"status": "active"|"not_configured"|"expired"|"plan_locked"|"quota_exceeded"}`

- [ ] **Step 1: Cek apakah `check_feature_status` sudah ada**

```bash
grep -rn "check_feature_status\|feature_status" backend/app/ --include="*.py" | grep -v test
```

Catat path dan signature function yang ditemukan.

- [ ] **Step 2: Buat `features.py` router**

Buat `backend/app/routers/features.py`:
```python
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.base import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/features", tags=["features"])

KNOWN_FEATURES = {
    "facebook_engagement",
    "instagram_posting",
    "whatsapp_messaging",
}


@router.get("/{feature_name}")
async def get_feature_status(
    feature_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[dict]:
    tenant_id: str = request.state.tenant_id

    # Jika check_feature_status sudah ada di codebase, import dan pakai:
    # from app.services.feature_service import check_feature_status
    # status = await check_feature_status(tenant_id, feature_name, db)

    # Sementara: return "active" untuk semua fitur yang dikenal (akan diupdate di Fase 3)
    if feature_name not in KNOWN_FEATURES:
        return APIResponse(data={"status": "not_configured"})

    return APIResponse(data={"status": "active"})
```

> Jika Step 1 menemukan `check_feature_status` yang sudah ada, import dan gunakan function tersebut dan hapus logika placeholder di atas.

- [ ] **Step 3: Daftarkan router di `main.py`**

Edit `backend/app/main.py`:
```python
from app.routers import auth, conversations, features, webhooks
# ...
app.include_router(features.router)
```

- [ ] **Step 4: Buat test**

Buat `backend/tests/test_features_router.py`:
```python
def test_known_feature_returns_active(client, valid_access_token):
    response = client.get(
        "/api/v1/features/facebook_engagement",
        cookies={"access_token": valid_access_token},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "active"


def test_unknown_feature_returns_not_configured(client, valid_access_token):
    response = client.get(
        "/api/v1/features/unknown_feature_xyz",
        cookies={"access_token": valid_access_token},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "not_configured"


def test_feature_endpoint_requires_auth(client):
    response = client.get("/api/v1/features/facebook_engagement")
    assert response.status_code == 401
```

- [ ] **Step 5: Jalankan test**

```bash
cd backend && python -m pytest tests/test_features_router.py -v
```

Expected: semua PASS.

- [ ] **Step 6: Jalankan full test suite untuk pastikan tidak ada regresi**

```bash
cd backend && python -m pytest -v
```

Expected: semua 67+ test PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/features.py backend/app/main.py backend/tests/test_features_router.py
git commit -m "feat: GET /api/v1/features/{name} — feature status endpoint"
```

---

## Task 4: Frontend — Scaffold + PRODUCT.md

**Files:**
- Create: `frontend/` (semua file scaffold)
- Create: `frontend/PRODUCT.md`
- Create: `frontend/vite.config.ts`

**Interfaces:**
- Produces: project React + Vite berjalan di `http://localhost:5173`, proxy ke backend `http://localhost:8000`

- [ ] **Step 1: Scaffold React + Vite + TypeScript**

```bash
cd /home/px/Projects/Reseller
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install axios zustand react-router-dom
npm install -D tailwindcss postcss autoprefixer @types/node
npx tailwindcss init -p
```

- [ ] **Step 3: Install shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
# Pilih: TypeScript=Yes, style=Default, base color=Slate, CSS variables=Yes
# src/index.css sebagai global CSS
```

Install komponen yang dibutuhkan:
```bash
npx shadcn@latest add button badge alert table switch label input card toast
```

- [ ] **Step 4: Konfigurasi Tailwind**

Edit `frontend/tailwind.config.ts`:
```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 5: Konfigurasi Vite proxy ke backend**

Edit `frontend/vite.config.ts`:
```ts
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

- [ ] **Step 6: Buat `PRODUCT.md` untuk Impeccable**

Buat `frontend/PRODUCT.md`:
```markdown
# Product Context — Reseller AI Dashboard

## Target Users
Reseller UMKM Indonesia yang mengelola toko online di Facebook/Instagram.
Pengguna tidak selalu tech-savvy. Bahasa Indonesia sebagai bahasa utama UI.

## Brand Voice
Profesional tapi tidak kaku. Ringan, langsung ke poin. Tidak pakai jargon teknis.
Hindari bahasa yang terlalu formal atau terlalu kasual.

## UI Register
Product/dashboard — bukan editorial/marketing.
Prioritas: kejelasan informasi, efisiensi aksi, tidak ada dekorasi berlebih.

## Anti-References
- Gradient text pada heading atau label apapun
- Ghost card (card tanpa border atau shadow yang jelas)
- Over-rounding (rounded-full pada button besar, card, atau container)
- AI-default color palette (biru-ungu gradient default shadcn tanpa kustomisasi)
- Animasi yang mengalihkan perhatian dari konten

## Color Intent
- Neutral base (slate/gray) — konten utama
- Brand accent (satu warna saja, bukan gradien)
- Status: hijau=aktif, kuning=perlu perhatian, merah=error/eskalasi, abu=nonaktif
```

- [ ] **Step 7: Verifikasi dev server berjalan**

```bash
cd frontend && npm run dev
```

Expected: server berjalan di `http://localhost:5173` tanpa error.

- [ ] **Step 8: Commit**

```bash
cd /home/px/Projects/Reseller
git add frontend/
git commit -m "feat: scaffold frontend React + Vite + shadcn/ui + Impeccable PRODUCT.md"
```

---

## Task 5: Frontend — Axios Client + Auth Hooks

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useAuth.ts`

**Interfaces:**
- Produces:
  - `api` — Axios instance, default `withCredentials: true`, interceptor 401 → redirect `/login`
  - `useAuth()` → `{ isLoading: boolean, isAuthenticated: boolean, user: MeResponse | null, logout: () => Promise<void> }`

- [ ] **Step 1: Buat Axios client**

Buat `frontend/src/lib/api.ts`:
```ts
import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      window.location.href = "/login";
      return Promise.reject(error);
    }
    if (status === 403) {
      console.error("Akses ditolak");
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 2: Buat `useAuth` hook**

Buat `frontend/src/hooks/useAuth.ts`:
```ts
import { useEffect, useState } from "react";
import api from "@/lib/api";

interface MeResponse {
  user_id: string;
  tenant_id: string;
  role: string;
}

export function useAuth() {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<MeResponse | null>(null);

  useEffect(() => {
    api
      .get<{ data: MeResponse }>("/auth/me")
      .then((res) => setUser(res.data.data))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  async function logout() {
    await api.post("/auth/logout").catch(() => {});
    window.location.href = "/login";
  }

  return { isLoading, isAuthenticated: user !== null, user, logout };
}
```

- [ ] **Step 3: Verifikasi TypeScript compile tanpa error**

```bash
cd frontend && npx tsc --noEmit
```

Expected: tidak ada error.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/hooks/useAuth.ts
git commit -m "feat: Axios client + useAuth hook"
```

---

## Task 6: Frontend — Router + Login Page

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/pages/Login.tsx`

**Interfaces:**
- Consumes: `useAuth()` dari Task 5
- Produces:
  - `/login` → Login page
  - `/inbox` → protected, redirect ke `/login` jika tidak authenticated
  - `/` → redirect ke `/inbox`

- [ ] **Step 1: Buat `main.tsx`**

Buat `frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

- [ ] **Step 2: Buat `App.tsx` dengan protected route**

Buat `frontend/src/App.tsx`:
```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import Login from "@/pages/Login";
import Inbox from "@/pages/Inbox";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) return <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">Memuat...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/inbox" element={<ProtectedRoute><Inbox /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/inbox" replace />} />
    </Routes>
  );
}
```

- [ ] **Step 3: Buat `Login.tsx`**

Buat `frontend/src/pages/Login.tsx`:
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import api from "@/lib/api";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await api.post("/auth/login", { email, password });
      navigate("/inbox", { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.message ?? "Email atau password salah.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm border border-slate-200 shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold text-slate-900">Masuk ke Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="border-slate-300"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="border-slate-300"
              />
            </div>
            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}
            <Button type="submit" disabled={isLoading} className="w-full bg-slate-900 text-white hover:bg-slate-800">
              {isLoading ? "Memproses..." : "Masuk"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Jalankan Impeccable detect**

```bash
cd frontend && npx impeccable detect src/
```

Fix semua temuan sebelum lanjut.

- [ ] **Step 5: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/pages/Login.tsx
git commit -m "feat: router setup + Login page"
```

---

## Task 7: Frontend — FeatureGate Component

**Files:**
- Create: `frontend/src/hooks/useFeatureStatus.ts`
- Create: `frontend/src/components/FeatureGate.tsx`

**Interfaces:**
- Produces:
  - `useFeatureStatus(feature: string)` → `{ status: FeatureStatus, isLoading: boolean }`
  - `<FeatureGate feature="facebook_engagement">` — render children jika active, alert jika tidak

- [ ] **Step 1: Buat `useFeatureStatus` hook**

Buat `frontend/src/hooks/useFeatureStatus.ts`:
```ts
import { useEffect, useState } from "react";
import api from "@/lib/api";

type FeatureStatus = "active" | "not_configured" | "expired" | "plan_locked" | "quota_exceeded";

export function useFeatureStatus(feature: string): { status: FeatureStatus; isLoading: boolean } {
  const [status, setStatus] = useState<FeatureStatus>("not_configured");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ data: { status: FeatureStatus } }>(`/features/${feature}`)
      .then((res) => setStatus(res.data.data.status))
      .catch(() => setStatus("not_configured"))
      .finally(() => setIsLoading(false));
  }, [feature]);

  return { status, isLoading };
}
```

- [ ] **Step 2: Buat `FeatureGate` component**

Buat `frontend/src/components/FeatureGate.tsx`:
```tsx
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useFeatureStatus } from "@/hooks/useFeatureStatus";

type StatusConfig = {
  title: string;
  desc: string;
  action?: string;
  href?: string;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  not_configured: {
    title: "Belum terhubung",
    desc: "Hubungkan integrasi ini untuk mengaktifkan fitur.",
    action: "Buka Settings",
    href: "/settings/integrations",
  },
  expired: {
    title: "Koneksi kedaluwarsa",
    desc: "Sambungkan ulang akun kamu untuk melanjutkan.",
    action: "Reconnect",
    href: "/settings/integrations",
  },
  plan_locked: {
    title: "Tersedia di plan lebih tinggi",
    desc: "Upgrade untuk mengakses fitur ini.",
    action: "Lihat Plan",
    href: "/billing",
  },
  quota_exceeded: {
    title: "Kuota bulan ini sudah habis",
    desc: "Upgrade atau tunggu reset bulan depan.",
    action: "Upgrade Plan",
    href: "/billing",
  },
};

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
}

export function FeatureGate({ feature, children }: FeatureGateProps) {
  const { status, isLoading } = useFeatureStatus(feature);

  if (isLoading) {
    return <div className="h-10 animate-pulse rounded-md bg-slate-100" />;
  }

  if (status === "active") return <>{children}</>;

  const cfg = STATUS_CONFIG[status];
  if (!cfg) return null;

  return (
    <Alert className="flex items-start justify-between gap-4 border-slate-200 bg-slate-50">
      <div>
        <AlertTitle className="text-sm font-medium text-slate-900">{cfg.title}</AlertTitle>
        <AlertDescription className="text-sm text-slate-500">{cfg.desc}</AlertDescription>
      </div>
      {cfg.action && (
        <Button size="sm" variant="outline" asChild className="shrink-0 border-slate-300 text-slate-700">
          <a href={cfg.href}>{cfg.action}</a>
        </Button>
      )}
    </Alert>
  );
}
```

- [ ] **Step 3: Jalankan Impeccable detect**

```bash
cd frontend && npx impeccable detect src/
```

Fix semua temuan.

- [ ] **Step 4: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useFeatureStatus.ts frontend/src/components/FeatureGate.tsx
git commit -m "feat: FeatureGate component + useFeatureStatus hook (RULE-07)"
```

---

## Task 8: Frontend — Inbox Page

**Files:**
- Create: `frontend/src/store/inbox.ts`
- Create: `frontend/src/hooks/useConversations.ts`
- Create: `frontend/src/pages/Inbox.tsx`

**Interfaces:**
- Consumes: `<FeatureGate>` dari Task 7, `useAuth()` dari Task 5
- Produces: `/inbox` — tabel percakapan dengan filter + toggle takeover, polling 10 detik

- [ ] **Step 1: Buat Zustand store**

Buat `frontend/src/store/inbox.ts`:
```ts
import { create } from "zustand";

export interface ConversationResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  platform: string;
  channel_type: string;
  message_in: string | null;
  message_out: string | null;
  intent: string | null;
  sentiment: string | null;
  is_human_takeover: boolean;
  escalation_reason: string | null;
  created_at: string;
}

type Filter = "all" | "ai" | "human";

interface InboxStore {
  conversations: ConversationResponse[];
  filter: Filter;
  setConversations: (c: ConversationResponse[]) => void;
  setFilter: (f: Filter) => void;
  toggleTakeover: (id: string, value: boolean) => void;
}

export const useInboxStore = create<InboxStore>((set) => ({
  conversations: [],
  filter: "all",
  setConversations: (conversations) => set({ conversations }),
  setFilter: (filter) => set({ filter }),
  toggleTakeover: (id, value) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, is_human_takeover: value } : c
      ),
    })),
}));
```

- [ ] **Step 2: Buat `useConversations` hook**

Buat `frontend/src/hooks/useConversations.ts`:
```ts
import { useEffect } from "react";
import api from "@/lib/api";
import { useInboxStore, type ConversationResponse } from "@/store/inbox";

export function useConversations() {
  const { filter, setConversations, toggleTakeover } = useInboxStore();

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter === "ai") params.is_human_takeover = "false";
    if (filter === "human") params.is_human_takeover = "true";

    function fetch() {
      api
        .get<{ data: ConversationResponse[] }>("/conversations", { params })
        .then((res) => setConversations(res.data.data))
        .catch(() => {});
    }

    fetch();
    const timer = setInterval(fetch, 10_000);
    return () => clearInterval(timer);
  }, [filter, setConversations]);

  async function handleToggle(id: string, currentValue: boolean) {
    const newValue = !currentValue;
    toggleTakeover(id, newValue); // optimistic update
    try {
      await api.patch(`/conversations/${id}/takeover`, { is_human_takeover: newValue });
    } catch {
      toggleTakeover(id, currentValue); // revert
    }
  }

  return { handleToggle };
}
```

- [ ] **Step 3: Buat `Inbox.tsx`**

Buat `frontend/src/pages/Inbox.tsx`:
```tsx
import { FeatureGate } from "@/components/FeatureGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { useConversations } from "@/hooks/useConversations";
import { useInboxStore } from "@/store/inbox";

const FILTER_LABELS = { all: "Semua", ai: "AI", human: "Human" } as const;

function truncate(text: string | null, max: number) {
  if (!text) return "—";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function relativeTime(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d yang lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m yang lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j yang lalu`;
  return `${Math.floor(diff / 86400)}h yang lalu`;
}

function sentimentVariant(s: string | null): "default" | "secondary" | "destructive" {
  if (s === "positive") return "default";
  if (s === "negative") return "destructive";
  return "secondary";
}

export default function Inbox() {
  const { logout } = useAuth();
  const { conversations, filter, setFilter } = useInboxStore();
  const { handleToggle } = useConversations();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-900">Reseller AI — Inbox</span>
        <Button variant="ghost" size="sm" onClick={logout} className="text-slate-500 hover:text-slate-900">
          Keluar
        </Button>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
        <FeatureGate feature="facebook_engagement">
          <div className="mb-4 flex gap-2">
            {(["all", "ai", "human"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                className={filter === f ? "bg-slate-900 text-white" : "border-slate-300 text-slate-600"}
              >
                {FILTER_LABELS[f]}
              </Button>
            ))}
          </div>

          <div className="rounded-md border border-slate-200 bg-white shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-200">
                  <TableHead className="text-xs font-medium text-slate-500">Platform</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Pesan masuk</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Intent</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Sentiment</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Status</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Waktu</TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">Human takeover</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="py-10 text-center text-sm text-slate-400">
                      Belum ada percakapan.
                    </TableCell>
                  </TableRow>
                )}
                {conversations.map((conv) => (
                  <TableRow key={conv.id} className="border-slate-100">
                    <TableCell className="text-sm text-slate-700 capitalize">{conv.platform}</TableCell>
                    <TableCell className="max-w-xs text-sm text-slate-600">{truncate(conv.message_in, 80)}</TableCell>
                    <TableCell>
                      {conv.intent ? (
                        <Badge variant="secondary" className="text-xs">{conv.intent}</Badge>
                      ) : <span className="text-slate-300">—</span>}
                    </TableCell>
                    <TableCell>
                      {conv.sentiment ? (
                        <Badge variant={sentimentVariant(conv.sentiment)} className="text-xs">{conv.sentiment}</Badge>
                      ) : <span className="text-slate-300">—</span>}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={conv.is_human_takeover ? "destructive" : "secondary"}
                        className="text-xs"
                      >
                        {conv.is_human_takeover ? "Human" : "AI"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">{relativeTime(conv.created_at)}</TableCell>
                    <TableCell>
                      <Switch
                        checked={conv.is_human_takeover}
                        onCheckedChange={() => handleToggle(conv.id, conv.is_human_takeover)}
                        aria-label="Toggle human takeover"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </FeatureGate>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Jalankan Impeccable detect**

```bash
cd frontend && npx impeccable detect src/
```

Fix semua temuan sebelum lanjut.

- [ ] **Step 5: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/store/inbox.ts frontend/src/hooks/useConversations.ts frontend/src/pages/Inbox.tsx
git commit -m "feat: Inbox page — tabel percakapan, filter, toggle takeover, polling 10 detik"
```

---

## Task 9: End-to-End Verification

**Files:** Tidak ada file baru — hanya verifikasi.

- [ ] **Step 1: Jalankan backend**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Jalankan frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Test login flow**

Buka `http://localhost:5173`. Ekspektasi:
- Redirect ke `/login` otomatis
- Submit form login dengan kredensial valid → redirect ke `/inbox`
- Cookie `access_token` + `refresh_token` ada di browser DevTools → Application → Cookies

- [ ] **Step 4: Test Inbox**

Di halaman Inbox:
- Tabel tampil (atau pesan "Belum ada percakapan" jika kosong)
- Filter Semua/AI/Human berfungsi
- Toggle switch mengirim PATCH ke backend (cek Network tab)

- [ ] **Step 5: Test logout**

Klik "Keluar" → redirect ke `/login`, cookie hilang dari browser.

- [ ] **Step 6: Test protected route**

Hapus cookie manual → refresh `/inbox` → harus redirect ke `/login`.

- [ ] **Step 7: Final Impeccable scan**

```bash
cd frontend && npx impeccable detect src/
```

Expected: 0 violations.

- [ ] **Step 8: Final backend test suite**

```bash
cd backend && python -m pytest -v
```

Expected: semua PASS.

- [ ] **Step 9: Commit final**

```bash
git add -p  # review semua perubahan
git commit -m "feat: Fase 2 frontend selesai — Login + Inbox + httpOnly cookie auth"
```
