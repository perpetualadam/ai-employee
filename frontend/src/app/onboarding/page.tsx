"use client";

import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  PhoneCall,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { OnboardingProgress, onboardingSteps } from "@/components/onboarding/onboarding-progress";
import { OnboardingShell } from "@/components/onboarding/onboarding-shell";
import { OnboardingSkeleton } from "@/components/onboarding/onboarding-skeleton";
import { PhoneProvisioningPanel } from "@/components/phone-provisioning-panel";
import { TimezoneSelect } from "@/components/timezone-select";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, Business, CountryOption, TradeOption } from "@/lib/api";
import { cn } from "@/lib/utils";

const welcomePoints = [
  "14-day free trial included",
  "No credit card required to start",
  "Works with your existing phone number",
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
    currency: "USD",
    phone_number: "",
    escalation_phone: "",
    ai_instructions: "",
  });

  const StepIcon = onboardingSteps[step]?.icon;

  function applyCountryDefaults(countryCode: string, countryList: CountryOption[]) {
    const match = countryList.find((c) => c.code === countryCode);
    if (!match?.timezone) return {};
    return {
      country: countryCode,
      timezone: match.timezone,
      currency: match.currency ?? "USD",
    };
  }

  useEffect(() => {
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
          currency: biz.currency || "USD",
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

  const tradeOptions =
    trades.length > 0
      ? trades
      : [{ value: form.industry, label: form.industry, services: [], emergency_rules: [] }];

  const countryOptions =
    countries.length > 0
      ? countries
      : [{ code: form.country, label: form.country }];

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
      currency: form.currency,
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
      <OnboardingShell>
        <OnboardingSkeleton />
      </OnboardingShell>
    );
  }

  return (
    <OnboardingShell>
      <div className="space-y-8 animate-in fade-in duration-300">
        <OnboardingProgress currentStep={step} />

        <Card className="overflow-hidden border-border/80 shadow-sm">
          <CardHeader className="border-b border-border/60 bg-muted/20">
            <div className="flex items-start gap-4">
              {StepIcon && (
                <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <StepIcon className="size-5" aria-hidden />
                </div>
              )}
              <div>
                <CardTitle className="font-heading text-xl">
                  {onboardingSteps[step].title}
                </CardTitle>
                <CardDescription className="mt-1">
                  {onboardingSteps[step].description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            {step === 0 && (
              <div className="space-y-6">
                <p className="leading-relaxed text-muted-foreground">
                  In the next few minutes you&apos;ll configure your AI receptionist to
                  answer calls, book jobs, and update your CRM — just like a real
                  employee.
                </p>
                <ul className="space-y-3">
                  {welcomePoints.map((point) => (
                    <li key={point} className="flex items-center gap-3 text-sm">
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-success/10 text-success">
                        <Check className="size-3.5" aria-hidden />
                      </span>
                      {point}
                    </li>
                  ))}
                </ul>
                <Button onClick={() => goToStep(1)} className="w-full sm:w-auto">
                  Get started
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-5">
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
                  <Select
                    value={form.industry}
                    onValueChange={(value) =>
                      setForm({ ...form, industry: value ?? form.industry })
                    }
                  >
                    <SelectTrigger id="industry" className="w-full">
                      <SelectValue placeholder="Select your trade" />
                    </SelectTrigger>
                    <SelectContent>
                      {tradeOptions.map((trade) => (
                        <SelectItem key={trade.value} value={trade.value}>
                          {trade.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">Country</Label>
                  <Select
                    value={form.country}
                    onValueChange={(value) => {
                      if (!value) return;
                      setForm((prev) => ({
                        ...prev,
                        ...applyCountryDefaults(value, countries),
                      }));
                    }}
                  >
                    <SelectTrigger id="country" className="w-full">
                      <SelectValue placeholder="Select country" />
                    </SelectTrigger>
                    <SelectContent>
                      {countryOptions.map((country) => (
                        <SelectItem key={country.code} value={country.code}>
                          {country.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Sets address format, phone rules, and regional compliance for your
                    trade.
                  </p>
                </div>
                <TimezoneSelect
                  id="tz"
                  value={form.timezone}
                  onChange={(timezone) => setForm({ ...form, timezone })}
                  hint="Auto-filled when you pick a country — adjust if your shop is in a different timezone."
                />
                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => goToStep(0)}
                  >
                    <ArrowLeft className="size-4" />
                    Back
                  </Button>
                  <Button onClick={handleStep1Next} disabled={saving}>
                    {saving ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        Continue
                        <ArrowRight className="size-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-5">
                <p className="text-sm text-muted-foreground">
                  We&apos;ll add common services for your trade. The AI uses these when
                  booking appointments and quoting jobs.
                </p>
                <ul className="space-y-2 rounded-xl border border-border/80 bg-muted/20 p-4 text-sm">
                  {(selectedTrade?.services ?? ["General service call"]).map((svc) => (
                    <li key={svc} className="flex items-center gap-2">
                      <Check className="size-3.5 shrink-0 text-success" aria-hidden />
                      {svc}
                    </li>
                  ))}
                </ul>
                {selectedTrade && selectedTrade.emergency_rules.length > 0 && (
                  <p className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning-foreground">
                    Emergency rules: {selectedTrade.emergency_rules.join(", ")}
                  </p>
                )}
                <p className="text-sm text-muted-foreground">
                  You can add more services later in Settings.
                </p>
                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => goToStep(1)}
                  >
                    <ArrowLeft className="size-4" />
                    Back
                  </Button>
                  <Button onClick={handleStep2Next} disabled={saving}>
                    {saving ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Adding services...
                      </>
                    ) : (
                      <>
                        Add default services
                        <ArrowRight className="size-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
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
                    onChange={(e) =>
                      setForm({ ...form, escalation_phone: e.target.value })
                    }
                    placeholder="+15559876543"
                  />
                  <p className="text-xs text-muted-foreground">
                    Urgent calls transfer here when the AI escalates to a human.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="instructions">
                    Special instructions for AI (optional)
                  </Label>
                  <Textarea
                    id="instructions"
                    value={form.ai_instructions}
                    onChange={(e) =>
                      setForm({ ...form, ai_instructions: e.target.value })
                    }
                    placeholder="e.g. We don't work on Sundays. Always ask about warranty status."
                    rows={3}
                  />
                </div>
                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => goToStep(2)}
                  >
                    <ArrowLeft className="size-4" />
                    Back
                  </Button>
                  <Button onClick={handleStep3Next} disabled={saving}>
                    {saving ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        Continue
                        <ArrowRight className="size-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-5">
                <p className="text-sm text-muted-foreground">
                  Your AI receptionist is configured. Test it with a practice
                  conversation, then call your business number to hear it live.
                </p>
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm">
                  <p className="flex items-center gap-2 font-medium">
                    <PhoneCall className="size-4 text-primary" aria-hidden />
                    First-call checklist
                  </p>
                  <ol className="mt-3 space-y-2 text-muted-foreground">
                    <li>1. Test the AI in the receptionist simulator</li>
                    <li>2. Call your business number and book a test appointment</li>
                    <li>3. Check the appointment appears in Calendar</li>
                  </ol>
                </div>
                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => goToStep(3)}
                  >
                    <ArrowLeft className="size-4" />
                    Back
                  </Button>
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <Link
                      href="/dashboard/receptionist"
                      className={cn(buttonVariants({ variant: "outline" }), "justify-center")}
                    >
                      Test AI receptionist
                    </Link>
                    <Button onClick={handleComplete} disabled={saving}>
                      {saving ? (
                        <>
                          <Loader2 className="size-4 animate-spin" />
                          Finishing...
                        </>
                      ) : (
                        <>
                          Finish setup
                          <ArrowRight className="size-4" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <p
                className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                role="alert"
              >
                {error}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </OnboardingShell>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <OnboardingShell>
          <OnboardingSkeleton />
        </OnboardingShell>
      }
    >
      <OnboardingWizard />
    </Suspense>
  );
}
