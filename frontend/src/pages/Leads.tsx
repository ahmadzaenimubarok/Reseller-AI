import { useAuth } from "@/hooks/useAuth";
import { useLeads, type LeadResponse } from "@/hooks/useLeads";

const TIER_CONFIG = {
  hot: {
    label: "Panas",
    desc: "Sinyal niat beli kuat — prioritaskan follow-up",
    badge: "bg-red-100 text-red-700 border border-red-200",
    bar: "bg-red-500",
    dot: "bg-red-500",
    glow: "border-red-200",
  },
  warm: {
    label: "Hangat",
    desc: "Tertarik tapi belum memutuskan — pantau terus",
    badge: "bg-amber-100 text-amber-700 border border-amber-200",
    bar: "bg-amber-400",
    dot: "bg-amber-500",
    glow: "border-amber-200",
  },
  cold: {
    label: "Dingin",
    desc: "Belum ada sinyal minat — biarkan AI tangani",
    badge: "bg-slate-100 text-slate-600 border border-slate-200",
    bar: "bg-slate-300",
    dot: "bg-slate-400",
    glow: "border-slate-200",
  },
} as const;

const REASON_LABEL: Record<string, string> = {
  "niat_beli:positive": "Menyatakan niat beli dengan positif",
  "niat_beli:neutral": "Menyatakan niat beli",
  "niat_beli:negative": "Menyatakan niat beli, tapi ragu",
  "niat_beli:unknown": "Menyatakan niat beli",
  spam_only: "Hanya mengirim spam",
  no_interactions: "Belum ada interaksi",
  single_interaction: "Baru 1 kali interaksi",
  "decayed:hot_to_warm": "Tidak aktif lebih dari 1 hari",
  "decayed:warm_to_cold": "Tidak aktif lebih dari 2 hari",
};

const PLATFORM_LABEL: Record<string, string> = {
  facebook: "Facebook",
  messenger: "Messenger",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
};

function formatReason(raw: string | null) {
  if (!raw) return "—";
  if (raw.startsWith("tanya_info:")) {
    const count = raw.split(":")[1];
    return `Bertanya ${count}x tentang produk`;
  }
  return REASON_LABEL[raw] ?? raw;
}

function relativeTime(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  return `${Math.floor(diff / 86400)}h lalu`;
}

// Heatbar — representasi visual seberapa "panas" lead
function TierBar({ tier }: { tier: "hot" | "warm" | "cold" }) {
  const fill = tier === "hot" ? 100 : tier === "warm" ? 55 : 20;
  const cfg = TIER_CONFIG[tier];
  return (
    <div className="h-1 w-full rounded-full bg-slate-100 overflow-hidden">
      <div
        className={`h-full rounded-full ${cfg.bar} transition-all`}
        style={{ width: `${fill}%` }}
      />
    </div>
  );
}

function LeadCard({
  lead,
  onResolve,
  onArchive,
  showActions,
}: {
  lead: LeadResponse;
  onResolve: (id: string) => void;
  onArchive: (id: string) => void;
  showActions: boolean;
}) {
  const tier = TIER_CONFIG[lead.tier];
  const name = lead.customer_name ?? "Tanpa nama";
  const platform = PLATFORM_LABEL[lead.customer_platform ?? ""] ?? lead.customer_platform ?? "—";

  return (
    <div
      className={`rounded-xl border bg-white p-5 shadow-sm flex flex-col gap-4 transition-shadow hover:shadow-md ${tier.glow}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {/* Avatar inisial */}
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
              lead.tier === "hot"
                ? "bg-red-100 text-red-700"
                : lead.tier === "warm"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-slate-100 text-slate-600"
            }`}
          >
            {name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
            <p className="text-xs text-slate-400">{platform}</p>
          </div>
        </div>

        <span
          className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold border ${tier.badge}`}
        >
          {tier.label}
        </span>
      </div>

      {/* Heat bar */}
      <TierBar tier={lead.tier} />

      {/* Sinyal */}
      <div className="rounded-lg bg-slate-50 px-3 py-2.5">
        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400 mb-0.5">
          Sinyal
        </p>
        <p className="text-sm text-slate-700">{formatReason(lead.tier_reason)}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Interaksi
          </p>
          <p className="text-lg font-bold text-slate-900">{lead.interaction_count}</p>
          <p className="text-[11px] text-slate-400">total pesan</p>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Terakhir aktif
          </p>
          <p className="text-lg font-bold text-slate-900">
            {relativeTime(lead.last_interaction)}
          </p>
          <p className="text-[11px] text-slate-400">
            masuk {relativeTime(lead.created_at)}
          </p>
        </div>
      </div>

      {/* Actions */}
      {showActions && (
        <div className="flex gap-2 pt-1 border-t border-slate-100">
          <button
            onClick={() => onResolve(lead.id)}
            className="flex-1 rounded-md py-1.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors"
          >
            Tandai Selesai
          </button>
          <button
            onClick={() => onArchive(lead.id)}
            className="rounded-md px-3 py-1.5 text-xs font-semibold bg-white text-slate-500 border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            Arsip
          </button>
        </div>
      )}
    </div>
  );
}

const TIER_TABS = [
  { key: "all", label: "Semua" },
  { key: "hot", label: "Panas" },
  { key: "warm", label: "Hangat" },
  { key: "cold", label: "Dingin" },
] as const;

const STATUS_TABS = [
  { key: "active", label: "Aktif" },
  { key: "archived", label: "Diarsip" },
  { key: "resolved", label: "Selesai" },
] as const;

export default function Leads() {
  const { logout } = useAuth();
  const {
    leads,
    loading,
    tierFilter,
    setTierFilter,
    statusFilter,
    setStatusFilter,
    handleArchive,
    handleResolve,
  } = useLeads();

  const hotCount = leads.filter((l) => l.tier === "hot" && l.status === "active").length;
  const warmCount = leads.filter((l) => l.tier === "warm" && l.status === "active").length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <img src="/logo.jpeg" alt="Reseller AI" className="h-7 w-7 rounded-full object-cover" />
          <span className="text-sm font-semibold text-slate-900">Reseller AI — Leads</span>
          {hotCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse inline-block" />
              {hotCount} prospek panas
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <a href="/inbox" className="text-xs text-slate-500 hover:text-slate-900 transition-colors">
            Inbox
          </a>
          <button
            onClick={logout}
            className="text-xs text-slate-500 hover:text-slate-900 transition-colors"
          >
            Keluar
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
        {/* Summary bar */}
        {statusFilter === "active" && (hotCount > 0 || warmCount > 0) && (
          <div className="mb-6 flex gap-3">
            {hotCount > 0 && (
              <div className="flex items-center gap-2.5 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
                <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <div>
                  <p className="text-sm font-semibold text-red-700">{hotCount} prospek panas</p>
                  <p className="text-xs text-red-500">Perlu follow-up segera</p>
                </div>
              </div>
            )}
            {warmCount > 0 && (
              <div className="flex items-center gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                <div>
                  <p className="text-sm font-semibold text-amber-700">{warmCount} prospek hangat</p>
                  <p className="text-xs text-amber-600">Sedang tertarik, pantau terus</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filters */}
        <div className="mb-5 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="flex gap-1.5">
              {TIER_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTierFilter(t.key)}
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    tierFilter === t.key
                      ? "bg-slate-900 text-white shadow-sm"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
                  ].join(" ")}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex gap-1.5 border-l border-slate-200 pl-4">
              {STATUS_TABS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatusFilter(s.key)}
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    statusFilter === s.key
                      ? "bg-slate-100 text-slate-900 border border-slate-300"
                      : "text-slate-500 hover:text-slate-900",
                  ].join(" ")}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <span className="text-xs text-slate-400">
            {loading ? "Memuat..." : `${leads.length} leads`}
          </span>
        </div>

        {/* Tier desc */}
        {tierFilter !== "all" && (
          <p className="mb-4 text-xs text-slate-400">
            {TIER_CONFIG[tierFilter as keyof typeof TIER_CONFIG]?.desc}
          </p>
        )}

        {/* Grid */}
        {!loading && leads.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-20 text-sm text-slate-400">
            <span className="text-3xl">📋</span>
            <span>Belum ada lead di kategori ini.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {leads.map((lead) => (
              <LeadCard
                key={lead.id}
                lead={lead}
                onResolve={handleResolve}
                onArchive={handleArchive}
                showActions={statusFilter === "active"}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
