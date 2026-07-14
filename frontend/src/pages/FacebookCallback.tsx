import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useFacebookOAuth } from "@/hooks/useFacebookOAuth";
import type { FacebookPage } from "@/hooks/useFacebookOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

interface CallbackData {
  state: string;
  facebook_user_id: string | null;
  pages: FacebookPage[];
}

export default function FacebookCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { connectPage, loading, error: oauthError } = useFacebookOAuth();

  const [pages, setPages] = useState<FacebookPage[]>([]);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [step, setStep] = useState<"loading" | "select" | "connecting" | "done" | "error">(
    "loading"
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    // Cek apakah ada error dari backend
    const error = searchParams.get("error");
    if (error) {
      setStep("error");
      setErrorMessage("Authorization cancelled or failed.");
      return;
    }

    // Decode data dari backend redirect
    const data = searchParams.get("data");
    if (!data) {
      setStep("error");
      setErrorMessage("Data not found.");
      return;
    }

    try {
      const decoded: CallbackData = JSON.parse(atob(data));
      if (decoded.pages && decoded.pages.length > 0) {
        setPages(decoded.pages);
        setStep("select");
      } else {
        setStep("error");
        setErrorMessage("No Facebook Pages found.");
      }
    } catch {
      setStep("error");
      setErrorMessage("Failed to process data.");
    }
  }, [searchParams]);

  async function handleConnect() {
    if (!selectedPageId) return;

    const page = pages.find((p) => p.page_id === selectedPageId);
    if (!page) return;

    setStep("connecting");
    const success = await connectPage(page.page_id, page.page_name, page.access_token);
    if (success) {
      setStep("done");
      setTimeout(() => navigate("/settings"), 2000);
    } else {
      setStep("select");
    }
  }

  if (step === "loading") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
            <p className="text-slate-600">Processing authorization...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "error") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 text-4xl text-red-500">✕</div>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Failed</h2>
            <p className="text-slate-600">{errorMessage || oauthError}</p>
            <Button className="mt-4" onClick={() => navigate("/settings")} variant="outline">
              Back to Settings
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "select") {
    return (
      <AppLayout>
        <div className="mx-auto max-w-xl p-6">
          <h1 className="mb-4 text-xl font-semibold text-slate-900">Select Facebook Page</h1>
          <p className="mb-6 text-sm text-slate-500">
            Select the Page you want to connect to the system.
          </p>

          <div className="space-y-3">
            {pages.map((page) => (
              <label
                key={page.page_id}
                className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                  selectedPageId === page.page_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="page"
                  value={page.page_id}
                  checked={selectedPageId === page.page_id}
                  onChange={() => setSelectedPageId(page.page_id)}
                  className="h-4 w-4 text-blue-600"
                />
                <div>
                  <p className="font-medium text-slate-800">{page.page_name}</p>
                  <p className="text-xs text-slate-500">ID: {page.page_id}</p>
                </div>
              </label>
            ))}
          </div>

          {oauthError && <p className="mt-4 text-sm text-red-600">{oauthError}</p>}

          <div className="mt-6 flex gap-3">
            <Button onClick={handleConnect} disabled={!selectedPageId || loading}>
              {loading ? "Connecting..." : "Connect Page"}
            </Button>
            <Button variant="outline" onClick={() => navigate("/settings")}>
              Cancel
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (step === "connecting") {
    return (
      <AppLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
            <p className="text-slate-600">Connecting Page...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="mb-4 text-4xl text-green-500">✓</div>
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Success!</h2>
          <p className="text-slate-600">Facebook Page connected successfully.</p>
        </div>
      </div>
    </AppLayout>
  );
}
