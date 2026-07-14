import { useEffect, useState } from "react";
import { useFacebookOAuth } from "@/hooks/useFacebookOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function FacebookPages() {
  const { getLoginUrl, loading, error } = useFacebookOAuth();
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
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Connect Facebook</h1>
        <p className="mb-6 text-sm text-slate-500">
          Click the button below to connect your Facebook Page.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Facebook Page</h2>
          <p className="mb-4 text-sm text-slate-500">
            You'll be redirected to Facebook to grant access. After that, you can
            select the Page you want to connect.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Loading..." : "Connect Facebook"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
