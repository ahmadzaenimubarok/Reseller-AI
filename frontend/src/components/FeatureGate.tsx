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
    title: "Not connected",
    desc: "Connect this integration to enable the feature.",
    action: "Go to Settings",
    href: "/settings/integrations",
  },
  expired: {
    title: "Connection expired",
    desc: "Reconnect your account to continue.",
    action: "Reconnect",
    href: "/settings/integrations",
  },
  plan_locked: {
    title: "Available on a higher plan",
    desc: "Upgrade to access this feature.",
    action: "View Plan",
    href: "/billing",
  },
  quota_exceeded: {
    title: "Monthly quota exceeded",
    desc: "Upgrade or wait for monthly reset.",
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
