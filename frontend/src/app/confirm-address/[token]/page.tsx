"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, Check, Loader2, MapPin } from "lucide-react";
import { useParams } from "next/navigation";

import {
  CustomerErrorState,
  CustomerFormSkeleton,
  CustomerShell,
} from "@/components/customer/customer-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, AddressConfirmInfo } from "@/lib/api";

export default function ConfirmAddressPage() {
  const params = useParams();
  const token = params.token as string;
  const [info, setInfo] = useState<AddressConfirmInfo | null>(null);
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api
      .getAddressConfirmInfo(token)
      .then(setInfo)
      .catch(() => setError("This link is invalid or has expired."))
      .finally(() => setLoading(false));
  }, [token]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.submitAddressConfirm(token, address);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save address.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <CustomerFormSkeleton />;
  }

  if (error && !info) {
    return (
      <CustomerErrorState
        title="Link unavailable"
        message={error}
        actionLabel="Go to homepage"
        actionHref="/"
      />
    );
  }

  const confirmed = info?.already_confirmed || done;
  const displayAddress = done ? address : info?.confirmed_address;

  return (
    <CustomerShell
      businessName={info?.business_name ?? "Service request"}
      description={
        info?.customer_name
          ? `Confirm address for ${info.customer_name}`
          : "Confirm your service address"
      }
      badge="Address confirm"
    >
      <div className="mx-auto w-full max-w-md animate-in fade-in duration-300">
        <div className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
          <div className="border-b border-border/60 bg-muted/20 px-6 py-5">
            <div className="flex items-start gap-4">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                {confirmed ? (
                  <Check className="size-5" aria-hidden />
                ) : (
                  <MapPin className="size-5" aria-hidden />
                )}
              </div>
              <div>
                <h1 className="font-heading text-xl font-semibold">
                  {confirmed ? "Address confirmed" : "Confirm service address"}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  {confirmed
                    ? "You're all set — we'll use this address for your appointment."
                    : "Enter the full address where service is needed."}
                </p>
              </div>
            </div>
          </div>

          <div className="px-6 py-6">
            {confirmed ? (
              <div className="rounded-xl border border-success/30 bg-success/5 px-4 py-4 text-sm">
                <p className="font-medium text-foreground">Thank you!</p>
                <p className="mt-2 text-muted-foreground">
                  Your address{displayAddress ? ` (${displayAddress})` : ""} is confirmed.
                  You can close this page.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="address">Full service address</Label>
                  <Input
                    id="address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="123 Main St, Springfield, IL 62701"
                    required
                    autoComplete="street-address"
                  />
                  <p className="text-xs text-muted-foreground">
                    Include street, city, state, and ZIP so our team can find you.
                  </p>
                </div>
                {error && (
                  <p
                    className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                    role="alert"
                  >
                    {error}
                  </p>
                )}
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      Confirm address
                      <ArrowRight className="size-4" />
                    </>
                  )}
                </Button>
              </form>
            )}
          </div>
        </div>
      </div>
    </CustomerShell>
  );
}
