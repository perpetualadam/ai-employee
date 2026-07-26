"use client";

import { useCallback, useState } from "react";

import { PageHeader } from "@/components/dashboard/page-header";
import { TablePageSkeleton } from "@/components/dashboard/page-skeletons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";

type ProviderEntry = {
  service: string;
  name: string;
  configured: boolean;
  capabilities: {
    provider_name: string;
    supported_features: string[];
    country_support: string[];
    health_status: string;
  };
  health: {
    healthy: boolean;
    status: string;
    latency_ms?: number | null;
    version?: string;
  };
  latency_ms?: number | null;
  version?: string;
};

type ManagementResponse = {
  installed: ProviderEntry[];
  metrics: Array<Record<string, unknown>>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export default function AdminProvidersPage() {
  const { loading: authLoading } = useDashboardAuth();
  const [adminSecret, setAdminSecret] = useState("");
  const [data, setData] = useState<ManagementResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!adminSecret.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/admin/providers/management`, {
        headers: { "X-Cron-Secret": adminSecret.trim() },
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setData((await response.json()) as ManagementResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load providers");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [adminSecret]);

  const adminEnabled = process.env.NEXT_PUBLIC_ENABLE_ADMIN_UI === "true";

  async function handleLoad() {
    await load();
  }

  async function testProvider(service: string, name: string) {
    const response = await fetch(`${API_BASE}/admin/providers/test/${service}/${name}`, {
      method: "POST",
      headers: { "X-Cron-Secret": adminSecret.trim() },
      credentials: "include",
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    await load();
  }

  if (authLoading) {
    return <TablePageSkeleton />;
  }

  if (!adminEnabled) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center">
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Not found</h1>
        <p className="mt-2 text-muted-foreground">This page is not available.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-in fade-in duration-300">
      <PageHeader
        title="Provider management"
        description="Installed telecom providers, capabilities, health, and metrics"
      />

        <Card>
          <CardHeader>
            <CardTitle>Admin access</CardTitle>
            <CardDescription>
              Enter the backend CRON_SECRET for this session only — it is not stored in the browser
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="admin-secret">Admin secret</Label>
              <Input
                id="admin-secret"
                type="password"
                value={adminSecret}
                onChange={(e) => setAdminSecret(e.target.value)}
                placeholder="CRON_SECRET"
              />
            </div>
            <Button onClick={handleLoad} disabled={loading || !adminSecret.trim()}>
              {loading ? "Loading…" : "Load providers"}
            </Button>
          </CardContent>
        </Card>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {data ? (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Installed providers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.installed.map((entry) => (
                  <div key={`${entry.service}-${entry.name}`} className="rounded-lg border p-4 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium">
                        {entry.name} · {entry.service}
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => testProvider(entry.service, entry.name)}
                      >
                        Test connection
                      </Button>
                    </div>
                    <p className="mt-2 text-muted-foreground">
                      Health: {entry.health.status} · configured: {String(entry.configured)} · latency:{" "}
                      {entry.health.latency_ms ?? "—"}ms
                    </p>
                    <p className="mt-1 break-words">
                      Features: {entry.capabilities.supported_features.join(", ") || "none"}
                    </p>
                    <p className="mt-1 break-words">
                      Countries: {entry.capabilities.country_support.join(", ") || "default"}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {data.metrics.length ? (
              <Card>
                <CardHeader>
                  <CardTitle>Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="overflow-x-auto rounded bg-muted p-3 text-xs">
                    {JSON.stringify(data.metrics, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            ) : null}
          </>
        ) : null}
    </div>
  );
}
