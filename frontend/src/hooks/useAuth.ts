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
