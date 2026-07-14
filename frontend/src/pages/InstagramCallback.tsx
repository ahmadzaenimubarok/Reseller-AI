import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useInstagramOAuth } from "@/hooks/useInstagramOAuth";
import type { InstagramAccount } from "@/hooks/useInstagramOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

interface CallbackData {
  state: string;
  accounts: InstagramAccount[];
}

export default function InstagramCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { connectAccount, loading, error: oauthError } = useInstagramOAuth();

  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [step, setStep] = useState<"loading" | "select" | "connecting" | "done" | "error">(
    "loading"
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      setStep("error");
      setErrorMessage("Authorization cancelled or failed.");
      return;
    }

    const data = searchParams.get("data");
    if (!data) {
      setStep("error");
      setErrorMessage("Data not found.");
      return;
    }

    try {
      const decoded: CallbackData = JSON.parse(atob(data));
      if (decoded.accounts && decoded.accounts.length > 0) {
        setAccounts(decoded.accounts);
        setStep("select");
      } else {
        setStep("error");
        setErrorMessage(
          "No Instagram Business account found. Make sure your Instagram account is a Business Account connected to a Facebook Page."
        );
      }
    } catch {
      setStep("error");
      setErrorMessage("Failed to process data.");
    }
  }, [searchParams]);

  async function handleConnect() {
    if (!selectedAccountId) return;

    const account = accounts.find((a) => a.instagram_account_id === selectedAccountId);
    if (!account) return;

    setStep("connecting");
    const success = await connectAccount(
      account.page_id,
      account.page_name,
      account.page_token,
      account.instagram_account_id,
      account.instagram_username
    );
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
          <h1 className="mb-4 text-xl font-semibold text-slate-900">Select Instagram Account</h1>
          <p className="mb-6 text-sm text-slate-500">
            Select the Instagram Business account to connect.
          </p>

          <div className="space-y-3">
            {accounts.map((account) => (
              <label
                key={account.instagram_account_id}
                className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                  selectedAccountId === account.instagram_account_id
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="account"
                  value={account.instagram_account_id}
                  checked={selectedAccountId === account.instagram_account_id}
                  onChange={() => setSelectedAccountId(account.instagram_account_id)}
                  className="h-4 w-4 text-blue-600"
                />
                <div>
                  <p className="font-medium text-slate-800">
                    {account.instagram_name || account.instagram_username}
                  </p>
                  <p className="text-xs text-slate-500">
                    @{account.instagram_username} — via {account.page_name}
                  </p>
                </div>
              </label>
            ))}
          </div>

          {oauthError && <p className="mt-4 text-sm text-red-600">{oauthError}</p>}

          <div className="mt-6 flex gap-3">
            <Button onClick={handleConnect} disabled={!selectedAccountId || loading}>
              {loading ? "Connecting..." : "Connect Instagram"}
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
            <p className="text-slate-600">Connecting Instagram...</p>
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
          <p className="text-slate-600">Instagram connected successfully.</p>
        </div>
      </div>
    </AppLayout>
  );
}
