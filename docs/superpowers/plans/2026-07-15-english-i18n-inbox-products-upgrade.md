# Plan: English Standardization + Inbox & Products Upgrade

**Tanggal:** 15 Juli 2026
**Status:** Draft
**Fase:** 5b — UI/UX Improvement

---

## Ringkasan

Tiga pekerjaan utama:
1. **English Standardization** — Seluruh UI dan backend response menggunakan bahasa Inggris
2. **Inbox Upgrade** — Search, date filter, quick reply, conversation notes
3. **Products Upgrade** — Edit inline, bulk actions, image preview, product search

---

## Scope

### In Scope
- Ganti semua teks Indonesia di frontend ke bahasa Inggris
- Ganti semua error message & response di backend ke bahasa Inggris
- Inbox: search by customer name/message, date range filter, quick reply textarea, conversation notes
- Products: inline edit, bulk delete, product image display, search & filter

### Out of Scope
- i18n framework (react-i18next) — tidak perlu, cukup hardcode English
- Multi-language support — fokus English saja
- WhatsApp/TikTok integration

---

## Part 1: English Standardization

### 1.1 Frontend Text Changes

| File | Indonesian | English |
|------|-----------|---------|
| **Login.tsx** | | |
| | "Masuk ke Dashboard" | "Sign in to Dashboard" |
| | "Email atau password salah." | "Invalid email or password." |
| | "Memproses..." | "Signing in..." |
| | "Masuk" | "Sign in" |
| **Settings.tsx** | | |
| | "Pengaturan" | "Settings" |
| | "Terhubung" / "Belum terhubung" | "Connected" / "Not connected" |
| | "Hubungkan Facebook Page Anda untuk mengaktifkan auto-reply komentar dan Messenger DM." | "Connect your Facebook Page to enable auto-reply for comments and Messenger DM." |
| | "✓ Facebook Page terhubung" | "✓ Facebook Page connected" |
| | "Hubungkan Page Lain" | "Connect Another Page" |
| | "Hubungkan akun Instagram Business Anda untuk mengaktifkan auto-reply DM Instagram." | "Connect your Instagram Business account to enable auto-reply for Instagram DM." |
| | "✓ Instagram terhubung" | "✓ Instagram connected" |
| | "Hubungkan Akun Lain" | "Connect Another Account" |
| | "Hubungkan Shopify untuk mengimpor produk secara otomatis." | "Connect Shopify to automatically import products." |
| | "✓ Shopify terhubung" | "✓ Shopify connected" |
| | "Hubungkan Toko Lain" | "Connect Another Store" |
| **Products.tsx** | | |
| | "Produk" | "Products" |
| | "Nama produk wajib diisi." | "Product name is required." |
| | "Gagal menambahkan produk. Coba lagi." | "Failed to add product. Try again." |
| | "Import selesai: X produk diimport, Y produk diupdate." | "Import complete: X products imported, Y products updated." |
| | "Mengimport..." | "Importing..." |
| | "Import dari Shopify" | "Import from Shopify" |
| | "Batal" / "+ Tambah Produk" | "Cancel" / "+ Add Product" |
| | "Nama Produk *" | "Product Name *" |
| | "Deskripsi" | "Description" |
| | "Cocok untuk lari marathon..." | "Great for marathon running..." |
| | "Harga (Rp)" | "Price (Rp)" |
| | "Link Affiliate" | "Affiliate Link" |
| | "Menyimpan..." / "Simpan Produk" | "Saving..." / "Save Product" |
| | "Memuat produk..." | "Loading products..." |
| | "Belum ada produk. Tambahkan produk agar AI bisa menjawab pertanyaan customer." | "No products yet. Add products so AI can answer customer questions." |
| | "Aktif" / "Nonaktif" | "Active" / "Inactive" |
| | "Hapus" | "Delete" |
| **FacebookCallback.tsx** | | |
| | "Authorization dibatalkan atau gagal." | "Authorization cancelled or failed." |
| | "Data tidak ditemukan." | "Data not found." |
| | "Tidak ada Facebook Page yang ditemukan." | "No Facebook Pages found." |
| | "Gagal memproses data." | "Failed to process data." |
| | "Memproses authorization..." | "Processing authorization..." |
| | "Gagal" | "Failed" |
| | "Kembali ke Settings" | "Back to Settings" |
| | "Pilih Facebook Page" | "Select Facebook Page" |
| | "Pilih Page yang ingin dihubungkan ke sistem Omnichannel." | "Select the Page you want to connect to the system." |
| | "Menghubungkan..." / "Hubungkan Page" | "Connecting..." / "Connect Page" |
| | "Batal" | "Cancel" |
| | "Menghubungkan Page..." | "Connecting Page..." |
| | "Berhasil!" | "Success!" |
| | "Facebook Page berhasil dihubungkan." | "Facebook Page connected successfully." |
| **InstagramCallback.tsx** | | |
| | "Authorization dibatalkan atau gagal." | "Authorization cancelled or failed." |
| | "Data tidak ditemukan." | "Data not found." |
| | "Tidak ditemukan akun Instagram Business..." | "No Instagram Business account found..." |
| | "Gagal memproses data." | "Failed to process data." |
| | "Memproses authorization..." | "Processing authorization..." |
| | "Gagal" | "Failed" |
| | "Kembali ke Settings" | "Back to Settings" |
| | "Pilih Akun Instagram" | "Select Instagram Account" |
| | "Pilih akun Instagram Business yang ingin dihubungkan." | "Select the Instagram Business account to connect." |
| | "Menghubungkan..." / "Hubungkan Instagram" | "Connecting..." / "Connect Instagram" |
| | "Batal" | "Cancel" |
| | "Menghubungkan Instagram..." | "Connecting Instagram..." |
| | "Berhasil!" | "Success!" |
| | "Instagram berhasil dihubungkan." | "Instagram connected successfully." |
| **InstagramConnect.tsx** | | |
| | "Hubungkan Instagram" | "Connect Instagram" |
| | "Klik tombol di bawah untuk menghubungkan akun Instagram Business Anda." | "Click the button below to connect your Instagram Business account." |
| | "Anda akan diarahkan ke Meta..." | "You'll be redirected to Meta..." |
| | "Memuat..." | "Loading..." |
| **FacebookPages.tsx** | | |
| | "Hubungkan Facebook" | "Connect Facebook" |
| | "Klik tombol di bawah untuk menghubungkan Facebook Page Anda." | "Click the button below to connect your Facebook Page." |
| | "Anda akan diarahkan ke Facebook..." | "You'll be redirected to Facebook..." |
| | "Memuat..." | "Loading..." |
| **ShopifyConnect.tsx** | | |
| | "Masukkan nama toko Shopify Anda." | "Enter your Shopify store name." |
| | "Gagal membuat URL OAuth." | "Failed to create OAuth URL." |
| | "Gagal menghubungi server." | "Failed to connect to server." |
| | "Hubungkan Shopify" | "Connect Shopify" |
| | "Masukkan nama toko Shopify Anda untuk menghubungkan dengan Remindly AI." | "Enter your Shopify store name to connect with Remindly AI." |
| | "Nama Toko Shopify" | "Shopify Store Name" |
| | "Contoh: ..." | "Example: ..." |
| | "Batal" | "Cancel" |
| | "Mengalihkan..." / "Hubungkan" | "Redirecting..." / "Connect" |
| **ShopifyCallback.tsx** | | |
| | "Gagal menghubungkan Shopify: ..." | "Failed to connect Shopify: ..." |
| | "Data callback tidak ditemukan." | "Callback data not found." |
| | "Gagal menyimpan koneksi Shopify." | "Failed to save Shopify connection." |
| | "Gagal memproses data callback." | "Failed to process callback data." |
| | "Menghubungkan Shopify..." | "Connecting to Shopify..." |
| | "Berhasil!" | "Success!" |
| | "Shopify store berhasil dihubungkan..." | "Shopify store connected successfully..." |
| | "Gagal" | "Failed" |
| | "Kembali ke Pengaturan" | "Back to Settings" |
| **FeatureGate.tsx** | | |
| | "Belum terhubung" | "Not connected" |
| | "Hubungkan integrasi ini untuk mengaktifkan fitur." | "Connect this integration to enable the feature." |
| | "Buka Settings" | "Go to Settings" |
| | "Koneksi kedaluwarsa" | "Connection expired" |
| | "Sambungkan ulang akun kamu untuk melanjutkan." | "Reconnect your account to continue." |
| | "Tersedia di plan lebih tinggi" | "Available on a higher plan" |
| | "Upgrade untuk mengakses fitur ini." | "Upgrade to access this feature." |
| | "Lihat Plan" | "View Plan" |
| | "Kuota bulan ini sudah habis" | "Monthly quota exceeded" |
| | "Upgrade atau tunggu reset bulan depan." | "Upgrade or wait for monthly reset." |
| | "Upgrade Plan" | "Upgrade Plan" |
| **AppLayout.tsx** | | |
| | Code comment: "Badge merah di header Inbox..." | "Red badge in Inbox header..." |
| **Login.tsx** | | |
| | "Password" | "Password" |
| | "Email" | "Email" |
| **Terms.tsx & Privacy.tsx** | | |
| | Full Indonesian text | Keep as-is (legal documents, user can update later) |

### 1.2 Backend Response Changes

| File | Indonesian | English |
|------|-----------|---------|
| **routers/auth.py** | | |
| | "Akun berhasil dibuat. Selamat datang!" | "Account created successfully. Welcome!" |
| | "Refresh token tidak ditemukan." | "Refresh token not found." |
| | "Logout berhasil." | "Logged out successfully." |
| | "Token tidak ditemukan." | "Token not found." |
| | "Token tidak valid." | "Invalid token." |
| | "Tipe token tidak valid." | "Invalid token type." |
| **routers/products.py** | | |
| | "Produk berhasil ditambahkan." | "Product added successfully." |
| | "Produk tidak ditemukan." | "Product not found." |
| | "Produk berhasil dihapus." | "Product deleted successfully." |
| | "Import selesai: X produk diimport, Y produk diupdate." | "Import complete: X products imported, Y products updated." |
| | "Gagal import produk dari Shopify." | "Failed to import products from Shopify." |
| **routers/conversations.py** | | |
| | "Conversation tidak ditemukan." | "Conversation not found." |
| **routers/leads.py** | | |
| | "Lead tidak ditemukan." | "Lead not found." |
| **routers/billing.py** | | |
| | "Tenant tidak ditemukan." | "Tenant not found." |
| | "Plan berhasil diubah." | "Plan updated successfully." |
| | "Checkout session berhasil dibuat." | "Checkout session created successfully." |
| **routers/settings.py** | | |
| | "Facebook Page token berhasil disimpan." | "Facebook Page token saved successfully." |
| | "Instagram token berhasil disimpan." | "Instagram token saved successfully." |
| **routers/webhooks.py** | | |
| | "Verify token tidak valid." | "Invalid verify token." |
| | "Signature tidak valid." | "Invalid signature." |
| | "Payload tidak valid." | "Invalid payload." |
| | "object bukan page" | "object is not a page" |
| | "object bukan instagram" | "object is not instagram" |
| **routers/facebook_oauth.py** | | |
| | "Facebook Page berhasil dihubungkan." | "Facebook Page connected successfully." |
| | "Facebook connection berhasil dihapus." | "Facebook connection removed successfully." |
| **routers/instagram_oauth.py** | | |
| | "Instagram berhasil dihubungkan." | "Instagram connected successfully." |
| | "Instagram connection berhasil dihapus." | "Instagram connection removed successfully." |
| **routers/shopify_oauth.py** | | |
| | "Shopify store berhasil dihubungkan." | "Shopify store connected successfully." |
| | "Shopify connection berhasil dihapus." | "Shopify connection removed successfully." |
| **services/auth_service.py** | | |
| | "Email sudah terdaftar." | "Email already registered." |
| | "Email atau password salah." | "Invalid email or password." |
| | "Akun dinonaktifkan." | "Account is deactivated." |
| | "Refresh token tidak valid." | "Invalid refresh token." |
| | "Bukan refresh token." | "Not a refresh token." |
| | "User tidak ditemukan atau nonaktif." | "User not found or inactive." |
| **services/billing_service.py** | | |
| | "Tenant tidak ditemukan" | "Tenant not found" |
| | "Plan tidak valid: {plan}" | "Invalid plan: {plan}" |
| | "Plan yang dipilih sama dengan plan aktif" | "Selected plan is the same as current plan" |
| | "Downgrade ke plan ini sudah dijadwalkan" | "Downgrade to this plan is already scheduled" |
| | "Tidak dapat membaca periode berlangganan dari Stripe" | "Cannot read subscription period from Stripe" |
| | "Signature tidak valid" | "Invalid signature" |
| **services/product_service.py** | | |
| | "Shopify belum terhubung." | "Shopify is not connected." |
| **middleware/tenant_context.py** | | |
| | "Token tidak ditemukan." | "Token not found." |
| | "Token tidak valid atau sudah kedaluwarsa." | "Invalid or expired token." |
| | "Tipe token tidak valid." | "Invalid token type." |

### 1.3 Intentionally Kept in Indonesian

- **LLM prompts** (`openai_service.py`) — AI reply system prompts. Keep in Indonesian because the AI回复对象是 Indonesian customers. Changing these would affect AI behavior.
- **RAG context labels** (`rag_service.py`) — "Produk:", "Harga:", "Link beli:" — used in AI context, should match customer language.
- **Terms.tsx & Privacy.tsx** — Legal documents, user can manually update later.

---

## Part 2: Inbox Upgrade

### Current State
- Thread list with platform icon, customer name, message count, timestamp
- Filter: All / AI / Human
- Expand thread to see message history
- TakeoverButton: hold 600ms to toggle AI/Human per-message or per-session
- Intent & sentiment badges

### Upgrades

#### 2.1 Search Bar
- Search by customer name or message content
- Debounced input (300ms)
- Clear button

#### 2.2 Date Range Filter
- Filter conversations by date: Today, Last 7 days, Last 30 days, All time
- Buttons next to existing All/AI/Human filter

#### 2.3 Quick Reply
- Textarea di bawah expanded thread
- Send button → POST `/api/v1/conversations/{session_id}/reply`
- Backend: save message to DB, send via Facebook/Instagram API
- Disabled when in AI mode (show hint: "Switch to Human mode to reply")

#### 2.4 Conversation Notes
- Internal notes per conversation (not visible to customer)
- Backend: add `notes` column to `sessions` table
- UI: collapsible "Notes" section in expanded thread
- Auto-save on blur

### Backend Changes

```sql
-- Add notes column to sessions
ALTER TABLE sessions ADD COLUMN notes TEXT;
```

New endpoint:
```
POST /api/v1/conversations/{session_id}/reply  — send manual reply
PATCH /api/v1/conversations/{session_id}/notes  — save internal notes
```

### Frontend Changes

New components:
- `SearchBar` — debounced search input
- `DateFilter` — date range filter buttons
- `QuickReply` — textarea + send button
- `ConversationNotes` — collapsible notes section

Modified:
- `Inbox.tsx` — integrate new components
- `useConversations.ts` — add search, date filter, reply, notes handlers
- `store/inbox.ts` — add search, dateRange, notes state

---

## Part 3: Products Upgrade

### Current State
- Product list with name, description, price, affiliate link
- Add product form (manual)
- Shopify import button
- Status badge (Active/Inactive)
- Delete button

### Upgrades

#### 3.1 Inline Edit
- Click product name or price to edit inline
- Save on Enter or blur, cancel on Escape
- PATCH request to backend

#### 3.2 Search & Filter
- Search by product name
- Filter by source (All / Manual / Shopify)
- Filter by status (All / Active / Inactive)

#### 3.3 Product Image Display
- Show first product image thumbnail in product card
- Shopify products already have images from API
- Manual products: add optional image URL field

#### 3.4 Bulk Actions
- Checkbox per product
- Bulk delete selected
- Bulk status change (activate/deactivate)

### Backend Changes

Update `UpdateProductRequest` schema to include `supplier_link`:
```python
class UpdateProductRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    base_price: Decimal | None = Field(None, gt=0)
    affiliate_link: str | None = None
    supplier_link: str | None = None
    margin_estimate: Decimal | None = Field(None, ge=0)
    status: str | None = Field(None, pattern="^(active|inactive)$")
```

New endpoint:
```
POST /api/v1/products/bulk-delete  — delete multiple products
PATCH /api/v1/products/bulk-status  — update status for multiple products
```

### Frontend Changes

Modified:
- `Products.tsx` — inline edit, search, filter, bulk actions, image display
- `useProducts.ts` — add search, filter, bulk operations
- Product card: show image thumbnail, editable fields

---

## Implementation Phases

### Phase 1: English Standardization (Est. 2-3 hours)
- [ ] Frontend: update all Indonesian text to English (13 files)
- [ ] Backend: update all error messages & responses (12 files)
- [ ] Run frontend build + lint
- [ ] Run backend tests

### Phase 2: Inbox Upgrade (Est. 4-5 hours)
- [ ] Backend: add `notes` column migration
- [ ] Backend: create reply + notes endpoints
- [ ] Frontend: SearchBar component
- [ ] Frontend: DateFilter component
- [ ] Frontend: QuickReply component
- [ ] Frontend: ConversationNotes component
- [ ] Frontend: integrate all into Inbox page
- [ ] Tests

### Phase 3: Products Upgrade (Est. 3-4 hours)
- [ ] Backend: update UpdateProductRequest schema
- [ ] Backend: bulk delete + bulk status endpoints
- [ ] Frontend: inline edit
- [ ] Frontend: search & filter
- [ ] Frontend: product image display
- [ ] Frontend: bulk actions
- [ ] Tests

---

## File Changes Summary

### Phase 1 (English)
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Products.tsx`
- `frontend/src/pages/FacebookCallback.tsx`
- `frontend/src/pages/InstagramCallback.tsx`
- `frontend/src/pages/InstagramConnect.tsx`
- `frontend/src/pages/FacebookPages.tsx`
- `frontend/src/pages/ShopifyConnect.tsx`
- `frontend/src/pages/ShopifyCallback.tsx`
- `frontend/src/components/FeatureGate.tsx`
- `frontend/src/components/AppLayout.tsx`
- `frontend/src/lib/api.ts`
- `backend/app/routers/auth.py`
- `backend/app/routers/products.py`
- `backend/app/routers/conversations.py`
- `backend/app/routers/leads.py`
- `backend/app/routers/billing.py`
- `backend/app/routers/settings.py`
- `backend/app/routers/webhooks.py`
- `backend/app/routers/facebook_oauth.py`
- `backend/app/routers/instagram_oauth.py`
- `backend/app/routers/shopify_oauth.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/billing_service.py`
- `backend/app/services/product_service.py`
- `backend/app/middleware/tenant_context.py`

### Phase 2 (Inbox)
- `backend/alembic/versions/` — new migration
- `backend/app/routers/conversations.py` — +reply, +notes endpoints
- `backend/app/models/session.py` — +notes column
- `frontend/src/components/SearchBar.tsx` — new
- `frontend/src/components/DateFilter.tsx` — new
- `frontend/src/components/QuickReply.tsx` — new
- `frontend/src/components/ConversationNotes.tsx` — new
- `frontend/src/pages/Inbox.tsx` — modified
- `frontend/src/hooks/useConversations.ts` — modified
- `frontend/src/store/inbox.ts` — modified

### Phase 3 (Products)
- `backend/app/schemas/product.py` — +supplier_link
- `backend/app/routers/products.py` — +bulk endpoints
- `frontend/src/pages/Products.tsx` — modified
- `frontend/src/hooks/useProducts.ts` — modified

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing tests with English messages | Update test assertions to match new English messages |
| LLM behavior change if prompts accidentally modified | Keep AI prompts in Indonesian, document clearly |
| Bulk operations timeout on large datasets | Paginate bulk operations, max 100 per batch |
| Inline edit race conditions | Optimistic update with server reconciliation |
