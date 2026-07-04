# Lead Intelligence Engine — Design Spec
**Tanggal:** 4 Juli 2026
**Fase:** 3
**Status:** Approved

---

## Ringkasan

Tambahkan Lead Intelligence Engine: klasifikasi otomatis setiap customer yang berinteraksi di Facebook/Messenger menjadi tier **hot / warm / cold**, dengan dashboard Leads untuk reseller follow up manual. Tidak ada LLM call tambahan — tier dihitung dari intent + sentiment yang sudah tersedia dari Fase 2.

---

## Keputusan Desain

| Keputusan | Pilihan |
|-----------|---------|
| Timing klasifikasi | Async Celery task, chain setelah engagement worker |
| Lead granularity | 1 lead per customer per tenant (di-upsert tiap conversation baru) |
| Klasifikasi method | Rule-based deterministik dari intent + sentiment (zero LLM call) |
| Auto-decay | Celery Beat harian — hot→warm setelah 1 hari, warm→cold setelah 2 hari, cold→archived setelah 7 hari tanpa interaksi |
| Aksi manual | Arsipkan + Tandai Selesai (tidak ada override tier manual) |
| Feature flag | `lead_classification` — aktif di plan `pro` dan `enterprise` |

---

## 1. Data Model

### Tabel: `leads`

```sql
leads (
  id                UUID PK DEFAULT gen_random_uuid(),
  tenant_id         UUID FK → tenants(id) ON DELETE CASCADE NOT NULL,
  customer_id       UUID FK → customers(id) ON DELETE CASCADE NOT NULL,
  tier              VARCHAR(10) NOT NULL,       -- 'hot' | 'warm' | 'cold'
  tier_reason       TEXT,                        -- e.g. "niat_beli:positive", "tanya_info:2x"
  interaction_count INT NOT NULL DEFAULT 0,      -- total conversation count untuk customer ini
  last_interaction  TIMESTAMPTZ,                 -- created_at conversation terakhir
  status            VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active' | 'archived' | 'resolved'
  resolved_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (tenant_id, customer_id)               -- 1 lead per customer per tenant
)

CREATE INDEX ON leads (tenant_id, status, tier);
CREATE INDEX ON leads (tenant_id, last_interaction);
```

### Tier Rules (deterministik)

Dievaluasi dari semua conversations customer, dijalankan setiap ada conversation baru:

```
Prioritas dari atas ke bawah — ambil tier pertama yang match:

1. HOT   — ada ≥1 conversation dengan intent='niat_beli' AND sentiment='positive'
2. WARM  — ada ≥1 conversation dengan intent='niat_beli' (sentiment apapun)
         — ATAU total conversation ≥2 dengan intent='tanya_info'
3. COLD  — semua conversation intent='spam'
         — ATAU hanya 1 interaksi, intent='tanya_info', tidak ada follow-up
```

`tier_reason` diisi string deskriptif untuk debugging:
- `"niat_beli:positive"` → hot
- `"niat_beli:neutral"` → warm
- `"tanya_info:2x"` → warm
- `"single_interaction"` → cold
- `"spam_only"` → cold

### Auto-Decay (Celery Beat, tiap 1 hari pukul 03:00 WIB)

```
hot  → last_interaction < now() - 1 hari  → turun ke warm
warm → last_interaction < now() - 2 hari  → turun ke cold
cold → last_interaction < now() - 7 hari  → status = 'archived'
```

Decay tidak override jika ada conversation baru masuk dalam periode tersebut.

---

## 2. Backend

### File baru

```
backend/
├── app/
│   ├── models/lead.py
│   ├── schemas/lead.py
│   ├── services/lead_service.py
│   └── routers/leads.py
├── workers/
│   └── lead_worker.py
└── alembic/versions/
    └── <hash>_add_leads_table.py
```

### `app/models/lead.py`

SQLAlchemy model untuk tabel `leads`. Kolom sesuai skema di atas.

### `app/services/lead_service.py`

```python
async def upsert_lead(tenant_id: str, customer_id: str, db: AsyncSession) -> Lead:
    """
    Fetch semua conversations customer → hitung tier → INSERT atau UPDATE lead.
    Dipanggil dari lead_worker setelah setiap engagement event.
    """

async def archive_lead(lead_id: UUID, tenant_id: str, db: AsyncSession) -> Lead: ...
async def resolve_lead(lead_id: UUID, tenant_id: str, db: AsyncSession) -> Lead: ...
async def run_decay(db: AsyncSession) -> int:
    """Jalankan auto-decay untuk semua tenant. Return jumlah lead yang di-update."""
```

`_calculate_tier(conversations: list[Conversation]) -> tuple[str, str]` — pure function, testable tanpa DB.

### `workers/lead_worker.py`

```python
@celery_app.task(queue="engagement", max_retries=3, retry_backoff=True)
def classify_lead(tenant_id: str, customer_id: str) -> None:
    """Dipanggil setelah engagement worker selesai simpan conversation."""

@celery_app.task(queue="engagement")
def decay_leads() -> None:
    """Dipanggil Celery Beat tiap hari pukul 03:00 WIB."""
```

**Chaining di engagement_worker.py** — `classify_lead.delay()` dipanggil di `_run()` **setelah** `async with session.begin()` block selesai (conversation sudah committed ke DB). Jangan panggil di dalam `session.begin()` — kalau transaction rollback, lead task tidak boleh ikut terpicu.

```python
# Di engagement_worker.py _run(), setelah session.begin() block:
async with _Session() as session:
    async with session.begin():
        customer = await process_facebook_comment(...)  # return customer
# Di luar begin() — conversation sudah committed:
classify_lead.delay(tenant_id, str(customer_id))
```

Ini butuh `process_facebook_comment` dan `process_messenger_message` return `customer_id` (UUID string), bukan `None`.

### `app/routers/leads.py`

```
GET  /api/v1/leads
  Query params: tier (hot|warm|cold), status (active|archived|resolved), limit (default 50)
  Response: list[LeadResponse] — include customer name, platform, tier, interaction_count, last_interaction, status

PATCH /api/v1/leads/{id}/archive
  Body: (none)
  Aksi: set status='archived'

PATCH /api/v1/leads/{id}/resolve
  Body: (none)
  Aksi: set status='resolved', resolved_at=now()
```

Semua endpoint filter by `tenant_id` (RULE-03). Tidak ada endpoint yang return data lintas tenant.

### `app/core/feature_flags.py` — update `PLAN_FEATURES`

```python
PLAN_FEATURES = {
    "free":       ["instagram_reply"],
    "starter":    ["instagram_reply", "tiktok_reply"],
    "pro":        ["instagram_reply", "tiktok_reply", "facebook_reply",
                   "whatsapp_reply", "lead_classification", "analytics"],
    "enterprise": ["*"],
}
```

Plan `free`/`starter`: lead_worker tetap jalan, tapi `check_feature_status` return `PLAN_LOCKED` → tier default `cold`, tidak di-upsert.

### Celery Beat schedule — tambah ke `workers/celery_app.py`

```python
app.conf.beat_schedule = {
    "decay-leads-daily": {
        "task": "workers.lead_worker.decay_leads",
        "schedule": crontab(hour=20, minute=0),  # 03:00 WIB = 20:00 UTC
    },
}
```

---

## 3. Frontend

### File baru

```
frontend/src/
├── pages/Leads.tsx
└── hooks/useLeads.ts
```

### Visual System (Impeccable / PRODUCT.md constraints)

**Tier badge** — inline chip, bukan pill penuh:
```
hot  → bg-red-50   text-red-700   border border-red-200    "Hot"
warm → bg-amber-50 text-amber-700 border border-amber-200  "Warm"
cold → bg-slate-50 text-slate-500 border border-slate-200  "Cold"
```

**Row behavior:**
- Default: subtle border-bottom, tidak ada card wrapper per row
- Hover: `hover:bg-slate-50` — tidak ada animasi
- Aksi (Arsip, Selesai): `variant="ghost" size="sm"`, muncul hanya saat `group-hover` pada row
- Archived/resolved row: `opacity-60`, hanya tampil di filter "Arsip"

**Tidak boleh:**
- Gradient pada badge atau heading
- Shadow berlebih pada card
- Animasi pulse pada badge tier (hanya badge eskalasi di Inbox yang pulse)
- Warna yang terlalu jenuh (hindari `red-500` langsung — pakai `red-600` pada text, `red-50` pada bg)

### `src/hooks/useLeads.ts`

```typescript
// Polling 30 detik, filter: tier | status
useLeads(filter: { tier?: string; status?: string })
  → { leads, isLoading, archiveLead, resolveLead }
```

### `src/pages/Leads.tsx` — struktur

```
<header>
  "Reseller AI — Leads"
  [badge: X hot] — muncul jika ada hot lead aktif, bg-red-50 text-red-700 (tanpa pulse)
  [Keluar]

<filter bar>
  [Semua] [Hot] [Warm] [Cold] [Arsip]   |   "X leads"

<table>
  Kolom: Nama | Platform | Tier | Interaksi | Terakhir aktif | Aksi
  Row actions (group-hover): [Arsip] [Selesai]

<empty state>
  Jika belum ada lead: teks singkat, tidak ada ilustrasi
```

### Routing — update `App.tsx`

Tambah route `/leads` → `<Leads />`. Tambah link "Leads" di header (sejajar dengan link ke Inbox).

---

## 4. Testing

Prioritas test untuk `lead_service.py`:

```python
test_calculate_tier_hot()        # niat_beli + positive → hot
test_calculate_tier_warm_intent() # niat_beli + neutral → warm
test_calculate_tier_warm_repeat() # tanya_info ≥2x → warm
test_calculate_tier_cold()       # spam only → cold
test_upsert_creates_new_lead()
test_upsert_upgrades_tier()      # cold → warm saat ada conversation baru
test_decay_hot_to_warm()
test_decay_warm_to_cold()
test_decay_cold_to_archived()
```

`_calculate_tier` adalah pure function — test tanpa DB, cepat.

---

## 5. Checklist Implementasi

```
Backend:
[ ] Alembic migration: add leads table
[ ] app/models/lead.py
[ ] app/schemas/lead.py (LeadResponse, LeadListResponse)
[ ] app/services/lead_service.py (upsert_lead, archive, resolve, run_decay, _calculate_tier)
[ ] workers/lead_worker.py (classify_lead, decay_leads)
[ ] workers/celery_app.py — tambah beat_schedule decay_leads
[ ] app/routers/leads.py (GET /leads, PATCH archive, PATCH resolve)
[ ] app/main.py — register leads router
[ ] app/core/feature_flags.py — tambah lead_classification ke pro+
[ ] workers/engagement_worker.py — chain classify_lead.delay() setelah commit
[ ] tests/test_lead_service.py

Frontend:
[ ] src/hooks/useLeads.ts
[ ] src/pages/Leads.tsx
[ ] src/App.tsx — tambah route /leads + nav link
```
