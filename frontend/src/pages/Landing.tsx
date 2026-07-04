import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const FEATURES = [
  {
    title: "Product Discovery",
    desc: "AI memantau Google Trends dan marketplace setiap 6 jam — temukan produk hype sebelum kompetitor.",
  },
  {
    title: "Content & Publishing",
    desc: "Caption, visual, dan jadwal posting ke Instagram, TikTok, dan Facebook — otomatis sesuai brand kamu.",
  },
  {
    title: "Engagement Engine",
    desc: "Balas komentar dan DM 24/7 dengan konteks produk yang tepat. AI-mu tahu apa yang kamu jual.",
  },
  {
    title: "Sales Conversion",
    desc: "Deteksi niat beli dan kirim link produk di momen yang pas. Tidak ada calon pembeli yang kelewatan.",
  },
];

const STEPS = [
  { num: "1", title: "Daftar akun", desc: "Buat workspace dalam 2 menit. Tidak perlu kartu kredit." },
  { num: "2", title: "Connect Facebook Page", desc: "Hubungkan Facebook Page bisnis kamu. OAuth aman, token tersimpan terenkripsi." },
  { num: "3", title: "AI mulai bekerja", desc: "Engagement Engine aktif — AI balas komentar dan DM atas nama tokomu." },
];

const PLANS = [
  {
    name: "Free",
    price: "Gratis",
    features: ["1 akun sosmed", "10 AI post/bulan", "50 AI reply/bulan", "Dashboard basic"],
    highlight: false,
  },
  {
    name: "Starter",
    price: "Rp 149.000",
    features: ["3 akun sosmed", "60 AI post/bulan", "500 AI reply/bulan", "Analytics dasar", "1 niche"],
    highlight: true,
  },
  {
    name: "Pro",
    price: "Rp 399.000",
    features: ["10 akun sosmed", "300 AI post/bulan", "3.000 AI reply/bulan", "Multi-niche", "Custom AI tone", "Priority queue"],
    highlight: false,
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Header */}
      <header className="border-b border-slate-100 px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-sm font-semibold tracking-tight">Reseller AI</span>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Masuk</Link>
            </Button>
            <Button size="sm" className="bg-slate-900 text-white hover:bg-slate-700" asChild>
              <Link to="/login">Coba Gratis</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 py-20 text-center">
        <Badge variant="secondary" className="mb-4 text-xs">
          Untuk reseller UMKM Indonesia
        </Badge>
        <h1 className="mb-4 text-4xl font-bold leading-tight tracking-tight text-slate-900">
          Jual lebih banyak.<br />Tanpa kerja lebih keras.
        </h1>
        <p className="mb-8 text-base text-slate-500 max-w-xl mx-auto">
          AI yang membantu reseller otomatis temukan produk, buat konten, balas chat, dan konversi pembeli — 24 jam sehari.
        </p>
        <Button size="lg" className="bg-slate-900 text-white hover:bg-slate-700" asChild>
          <Link to="/login">Mulai Gratis — Tidak Perlu Kartu Kredit</Link>
        </Button>
      </section>

      {/* Features */}
      <section className="bg-slate-50 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-10 text-center text-2xl font-bold tracking-tight">
            Empat mesin AI dalam satu dashboard
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <Card key={f.title} className="border-slate-200 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-500">{f.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-10 text-center text-2xl font-bold tracking-tight">
            Tiga langkah untuk mulai
          </h2>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.num} className="text-center">
                <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
                  {s.num}
                </div>
                <h3 className="mb-2 text-sm font-semibold">{s.title}</h3>
                <p className="text-sm text-slate-500">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-slate-50 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-10 text-center text-2xl font-bold tracking-tight">Pilih plan yang sesuai</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {PLANS.map((p) => (
              <Card
                key={p.name}
                className={
                  p.highlight
                    ? "border-slate-900 shadow-md"
                    : "border-slate-200 shadow-sm"
                }
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold">{p.name}</CardTitle>
                    {p.highlight && (
                      <Badge className="bg-slate-900 text-xs text-white">Populer</Badge>
                    )}
                  </div>
                  <p className="text-xl font-bold text-slate-900">
                    {p.price}
                    {p.price !== "Gratis" && (
                      <span className="text-xs font-normal text-slate-400">/bulan</span>
                    )}
                  </p>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1">
                    {p.features.map((f) => (
                      <li key={f} className="text-xs text-slate-500">
                        · {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={
                      p.highlight
                        ? "mt-4 w-full bg-slate-900 text-white hover:bg-slate-700"
                        : "mt-4 w-full"
                    }
                    variant={p.highlight ? "default" : "outline"}
                    size="sm"
                    asChild
                  >
                    <Link to="/login">Mulai</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 px-6 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-2 text-center sm:flex-row sm:justify-between">
          <span className="text-xs text-slate-400">© 2026 Reseller AI. Semua hak dilindungi.</span>
          <div className="flex gap-4 text-xs text-slate-400">
            <Link to="/privacy" className="hover:text-slate-700">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-slate-700">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
