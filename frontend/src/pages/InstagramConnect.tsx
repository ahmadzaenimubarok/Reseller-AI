import { useEffect, useState } from "react";
import { useInstagramOAuth } from "@/hooks/useInstagramOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function InstagramConnect() {
  const { getLoginUrl, loading, error } = useInstagramOAuth();
  const [loginUrl, setLoginUrl] = useState<string | null>(null);

  useEffect(() => {
    getLoginUrl().then((url) => setLoginUrl(url));
  }, [getLoginUrl]);

  function handleConnect() {
    if (loginUrl) {
      window.location.href = loginUrl;
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6">
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Connect Instagram</h1>
        <p className="mb-6 text-sm text-slate-500">
          Click the button below to connect your Instagram Business account.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Instagram Business</h2>
          <p className="mb-4 text-sm text-slate-500">
            You'll be redirected to Meta to grant access. Make sure your Instagram account
            is a Business Account connected to a Facebook Page.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Loading..." : "Connect Instagram"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
