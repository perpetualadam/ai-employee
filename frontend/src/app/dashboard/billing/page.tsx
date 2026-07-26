"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { TablePageSkeleton } from "@/components/dashboard/page-skeletons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import { api, ApiError, BillingStatus } from "@/lib/api";

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground">
          {used} / {limit}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function BillingContent() {
  const { loading: authLoading } = useDashboardAuth();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const success = searchParams.get("success");
  const canceled = searchParams.get("canceled");

  const loadBilling = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getBillingStatus();
      setBilling(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading) loadBilling();
  }, [authLoading, loadBilling]);

  async function handleCheckout(plan: "starter" | "pro") {
    setActionLoading(plan);
    setError("");
    try {
      const { checkout_url } = await api.createCheckout(plan);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Checkout failed");
      setActionLoading(null);
    }
  }

  async function handlePortal() {
    setActionLoading("portal");
    setError("");
    try {
      const { portal_url } = await api.createBillingPortal();
      window.location.href = portal_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open billing portal");
      setActionLoading(null);
    }
  }

  if (authLoading || loading) {
    return <TablePageSkeleton />;
  }

  if (!billing) {
    return (
      <p className="text-destructive">{error || "Unable to load billing"}</p>
    );
  }

  const statusVariant =
    billing.is_active ? "secondary" : billing.subscription_status === "past_due" ? "destructive" : "outline";

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-in fade-in duration-300">
      <PageHeader
        title="Billing"
        description="Manage your subscription and usage"
      />

        {success && (
          <p className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            Subscription activated. Thank you!
          </p>
        )}
        {canceled && (
          <p className="rounded-lg border p-3 text-sm text-muted-foreground">
            Checkout canceled. You can subscribe anytime.
          </p>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Current plan</CardTitle>
                <CardDescription>{billing.plan_description}</CardDescription>
              </div>
              <Badge variant={statusVariant}>{billing.subscription_status.replace("_", " ")}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold capitalize">{billing.plan_tier}</span>
              <span className="text-muted-foreground">{billing.plan_label}</span>
            </div>

            {billing.subscription_status === "trialing" && billing.trial_ends_at && (
              <p className="text-sm text-muted-foreground">
                Free trial ends{" "}
                {new Date(billing.trial_ends_at).toLocaleDateString(undefined, {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}

            {billing.subscription_period_end && billing.subscription_status === "active" && (
              <p className="text-sm text-muted-foreground">
                Renews{" "}
                {new Date(billing.subscription_period_end).toLocaleDateString(undefined, {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}

            <div className="flex flex-wrap gap-3 pt-2">
              {billing.has_stripe_customer && (
                <Button
                  variant="outline"
                  onClick={handlePortal}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === "portal" ? "Opening..." : "Manage billing"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Usage this month</CardTitle>
            <CardDescription>Resets on the 1st of each month</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <UsageBar
              used={billing.usage.calls_this_month}
              limit={billing.usage.calls_limit}
              label="Calls handled"
            />
            <UsageBar
              used={billing.usage.ai_tool_calls_this_month}
              limit={billing.usage.ai_tool_calls_limit}
              label="AI tool calls"
            />
          </CardContent>
        </Card>

        {(!billing.is_active || billing.plan_tier === "starter") && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Starter</CardTitle>
                <CardDescription>For solo operators</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-2xl font-bold">
                  $49
                  <span className="text-sm font-normal text-muted-foreground">/mo</span>
                </p>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>100 calls / month</li>
                  <li>500 AI tool calls</li>
                  <li>CRM + calendar</li>
                </ul>
                <Button
                  className="w-full"
                  variant={billing.plan_tier === "starter" ? "default" : "outline"}
                  onClick={() => handleCheckout("starter")}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === "starter" ? "Redirecting..." : "Subscribe to Starter"}
                </Button>
              </CardContent>
            </Card>

            <Card className="border-primary">
              <CardHeader>
                <CardTitle>Pro</CardTitle>
                <CardDescription>For growing teams</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-2xl font-bold">
                  $99
                  <span className="text-sm font-normal text-muted-foreground">/mo</span>
                </p>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>500 calls / month</li>
                  <li>5,000 AI tool calls</li>
                  <li>Priority support</li>
                </ul>
                <Button
                  className="w-full"
                  onClick={() => handleCheckout("pro")}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === "pro" ? "Redirecting..." : "Subscribe to Pro"}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <BillingContent />
    </Suspense>
  );
}
