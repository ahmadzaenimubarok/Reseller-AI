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
        <AlertTitle className="text-sm font-medium text-slate-900">
          {cfg.title}
        </AlertTitle>
        <AlertDescription className="text-sm text-slate-500">
          {cfg.desc}
        </AlertDescription>
      </div>
      {cfg.action && (
        <Button
          size="sm"
          variant="outline"
          asChild
          className="shrink-0 border-slate-300 text-slate-700"
        >
          <a href={cfg.href}>{cfg.action}</a>
        </Button>
      )}
    </Alert>
  );
}
