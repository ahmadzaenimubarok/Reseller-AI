import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ShopifyConnect() {
  const navigate = useNavigate();
  const [shopDomain, setShopDomain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!shopDomain.trim()) {
      setError("Enter your Shopify store name.");
      return;
    }

    // Format domain: pastikan format .myshopify.com
    let domain = shopDomain.trim().toLowerCase();
    domain = domain.replace(/\.myshopify\.com$/, "");
    domain = `${domain}.myshopify.com`;

    setLoading(true);
    try {
      const res = await fetch(`/api/v1/auth/shopify/login?shop=${domain}`, {
        credentials: "include",
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        setError("Failed to create OAuth URL.");
        setLoading(false);
      }
    } catch {
      setError("Failed to connect to server.");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <span className="text-2xl">🛒</span>
            </div>
            <h1 className="text-xl font-semibold text-slate-900">Connect Shopify</h1>
            <p className="mt-2 text-sm text-slate-500">
              Enter your Shopify store name to connect with Remindly AI.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="shopDomain">Shopify Store Name</Label>
              <div className="mt-1 flex items-center">
                <Input
                  id="shopDomain"
                  value={shopDomain}
                  onChange={(e) => setShopDomain(e.target.value)}
                  placeholder="nama-toko"
                  className="rounded-r-none"
                />
                <span className="rounded-r-md border border-l-0 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                  .myshopify.com
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Example: "store-name" or "store-name.myshopify.com"
              </p>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate("/settings")}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button type="submit" className="flex-1" disabled={loading}>
                {loading ? "Redirecting..." : "Connect"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
