import { useEffect, useState } from "react";
import api from "@/lib/api";

type FeatureStatus =
  | "active"
  | "not_configured"
  | "expired"
  | "plan_locked"
  | "quota_exceeded";

export function useFeatureStatus(feature: string): {
  status: FeatureStatus;
  isLoading: boolean;
} {
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
