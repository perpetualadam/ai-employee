"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

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
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="py-10 text-center text-sm text-muted-foreground">{error}</CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Confirm service address</CardTitle>
          <CardDescription>
            {info?.business_name}
            {info?.customer_name ? ` · ${info.customer_name}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {info?.already_confirmed || done ? (
            <p className="text-sm">
              Thank you! Your address
              {info?.confirmed_address ? ` (${info.confirmed_address})` : ""} is confirmed.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="address">Full US service address</Label>
                <Input
                  id="address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="123 Main St, Springfield, IL 62701"
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Saving..." : "Confirm address"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
