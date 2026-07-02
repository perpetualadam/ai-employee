"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PhoneProvisioningPanel } from "@/components/phone-provisioning-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, Business, CountryOption, TradeOption } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

const STEPS = [
  { title: "Welcome", description: "Let's set up your AI employee" },
  { title: "Business", description: "Tell us about your company" },
  { title: "Services", description: "What jobs do you take?" },
  { title: "Phone", description: "Connect your phone line" },
  { title: "Go live", description: "Test and launch" },
];

function OnboardingWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const step = Math.min(4, Math.max(0, Number(searchParams.get("step") ?? 0)));

  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [countries, setCountries] = useState<CountryOption[]>([]);

  const [form, setForm] = useState({
    name: "",
    industry: "plumbing",
    country: "US",
    timezone: "America/New_York",
    phone_number: "",
    escalation_phone: "",
    ai_instructions: "",
  });

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .getBusiness()
      .then((biz) => {
        if (biz.onboarding_completed) {
          router.replace("/dashboard");
          return;
        }
        setBusiness(biz);
        setForm({
          name: biz.name.endsWith("'s Business") ? "" : biz.name,
          industry: biz.industry,
          country: biz.country || "US",
          timezone: biz.timezone,
          phone_number: biz.phone_number ?? "",
          escalation_phone: biz.escalation_phone ?? "",
          ai_instructions: biz.ai_instructions ?? "",
        });
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));

    Promise.all([api.getTrades(), api.getCountries()])
      .then(([tradeList, countryList]) => {
        setTrades(tradeList);
        setCountries(countryList);
      })
      .catch(() => {
        /* fallback: step 1 still works with business.industry string */
      });
  }, [router]);

  const selectedTrade =
    trades.find((t) => t.value === form.industry) ?? null;

  function goToStep(n: number) {
    router.push(`/onboarding?step=${n}`);
  }

  async function saveBusiness(fields: Partial<typeof form>) {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateBusiness({
        ...fields,
        phone_number: fields.phone_number || undefined,
        escalation_phone: fields.escalation_phone || undefined,
        ai_instructions: fields.ai_instructions || undefined,
      });
      setBusiness(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
      throw err;
    } finally {
      setSaving(false);
    }
  }

  async function handleStep1Next() {
    if (!form.name.trim()) {
      setError("Business name is required");
      return;
    }
    await saveBusiness({
      name: form.name,
      industry: form.industry,
      country: form.country,
      timezone: form.timezone,
    });
    goToStep(2);
  }

  async function handleStep2Next() {
    setSaving(true);
    try {
      await api.seedDefaults();
      goToStep(3);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add services");
    } finally {
      setSaving(false);
    }
  }

  async function handleStep3Next() {
    setSaving(true);
    setError("");
    try {
      const current = await api.getBusiness();
      if (!current.phone_number) {
        setError("Get or save a business phone number before continuing.");
        return;
      }
      await saveBusiness({
        escalation_phone: form.escalation_phone,
        ai_instructions: form.ai_instructions,
      });
      goToStep(4);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleComplete() {
    setSaving(true);
    try {
      await api.completeOnboarding();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to complete setup");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              AI
            </div>
            <span className="font-semibold">Setup wizard</span>
          </div>
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            Skip for now
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-4 py-8">
        {/* Progress */}
        <div className="mb-8 flex gap-2">
          {STEPS.map((s, i) => (
            <div key={s.title} className="flex-1">
              <div
                className={cn(
                  "h-1.5 rounded-full",
                  i <= step ? "bg-primary" : "bg-muted",
                )}
              />
              <p className="mt-2 hidden text-xs text-muted-foreground sm:block">{s.title}</p>
            </div>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{STEPS[step].title}</CardTitle>
            <CardDescription>{STEPS[step].description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {step === 0 && (
              <div className="space-y-4">
                <p className="text-muted-foreground">
                  In the next few minutes you&apos;ll configure your AI receptionist to answer calls,
                  book jobs, and update your CRM — just like a real employee.
                </p>
                <ul className="space-y-2 text-sm">
                  <li className="flex gap-2">
                    <span className="text-primary">✓</span> 14-day free trial included
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary">✓</span> No credit card required to start
                  </li>
                  <li className="flex gap-2">
                    <span className="text-primary">✓</span> Works with your existing phone number
                  </li>
                </ul>
                <Button onClick={() => goToStep(1)}>Get started</Button>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="biz-name">Business name</Label>
                  <Input
                    id="biz-name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Mike's Plumbing & Heating"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="industry">Trade</Label>
                  <select
                    id="industry"
                    value={form.industry}
                    onChange={(e) => setForm({ ...form, industry: e.target.value })}
                    className="h-8 w-full rounded-lg border border-input bg-background px-2 text-sm"
                  >
                    {(trades.length ? trades : [{ value: form.industry, label: form.industry, services: [], emergency_rules: [] }]).map(
                      (i) => (
                        <option key={i.value} value={i.value}>
                          {i.label}
                        </option>
                      ),
                    )}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">Country</Label>
                  <select
                    id="country"
                    value={form.country}
                    onChange={(e) => setForm({ ...form, country: e.target.value })}
                    className="h-8 w-full rounded-lg border border-input bg-background px-2 text-sm"
                  >
                    {(countries.length ? countries : [{ code: form.country, label: form.country }]).map(
                      (c) => (
                        <option key={c.code} value={c.code}>
                          {c.label}
                        </option>
                      ),
                    )}
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Sets address format, phone rules, and regional compliance for your trade.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tz">Timezone</Label>
                  <Input
                    id="tz"
                    value={form.timezone}
                    onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                  />
                </div>
                <Button onClick={handleStep1Next} disabled={saving}>
                  {saving ? "Saving..." : "Continue"}
                </Button>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  We&apos;ll add common services for your trade. The AI uses these when booking
                  appointments and quoting jobs.
                </p>
                <ul className="rounded-lg border p-4 text-sm space-y-2">
                  {(selectedTrade?.services ?? ["General service call"]).map((svc) => (
                    <li key={svc}>• {svc}</li>
                  ))}
                </ul>
                {selectedTrade && selectedTrade.emergency_rules.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Emergency rules: {selectedTrade.emergency_rules.join(", ")}
                  </p>
                )}
                <p className="text-sm text-muted-foreground">
                  You can add more services later in Settings.
                </p>
                <Button onClick={handleStep2Next} disabled={saving}>
                  {saving ? "Adding services..." : "Add default services"}
                </Button>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <PhoneProvisioningPanel
                  business={business}
                  onPhoneUpdated={(updated) => setBusiness(updated)}
                  compact
                />
                <div className="space-y-2">
                  <Label htmlFor="escalation">Your cell phone (escalation)</Label>
                  <Input
                    id="escalation"
                    value={form.escalation_phone}
                    onChange={(e) => setForm({ ...form, escalation_phone: e.target.value })}
                    placeholder="+15559876543"
                  />
                  <p className="text-xs text-muted-foreground">
                    Urgent calls transfer here.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="instructions">Special instructions for AI (optional)</Label>
                  <Textarea
                    id="instructions"
                    value={form.ai_instructions}
                    onChange={(e) => setForm({ ...form, ai_instructions: e.target.value })}
                    placeholder="e.g. We don't work on Sundays. Always ask about warranty status."
                    rows={3}
                  />
                </div>
                <Button onClick={handleStep3Next} disabled={saving}>
                  {saving ? "Saving..." : "Continue"}
                </Button>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Your AI receptionist is configured. Test it with a practice conversation, then
                  call your business number to hear it live.
                </p>
                <div className="rounded-lg border bg-muted/50 p-4 text-sm space-y-2">
                  <p className="font-medium">First-call checklist</p>
                  <ul className="space-y-1 text-muted-foreground">
                    <li>1. Test the AI in the receptionist simulator</li>
                    <li>2. Call your business number and book a test appointment</li>
                    <li>3. Check the appointment appears in Calendar</li>
                  </ul>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link
                    href="/dashboard/receptionist"
                    className={buttonVariants({ variant: "outline" })}
                  >
                    Test AI receptionist
                  </Link>
                  <Button onClick={handleComplete} disabled={saving}>
                    {saving ? "Finishing..." : "Finish setup"}
                  </Button>
                </div>
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <OnboardingWizard />
    </Suspense>
  );
}
