"use client";

import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/dashboard/shell";
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
import { api, ApiError } from "@/lib/api";

export default function SettingsPage() {
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [form, setForm] = useState({
    name: "",
    phone_number: "",
    escalation_phone: "",
    timezone: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (business) {
      setForm({
        name: business.name,
        phone_number: business.phone_number ?? "",
        escalation_phone: business.escalation_phone ?? "",
        timezone: business.timezone,
      });
    }
  }, [business]);

  async function handleSave() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.updateBusiness({
        name: form.name,
        phone_number: form.phone_number || undefined,
        escalation_phone: form.escalation_phone || undefined,
        timezone: form.timezone,
      });
      setMessage("Settings saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const publicApiUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? "http://localhost:8000";

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <DashboardShell businessName={businessName}>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Business profile and voice setup</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Business profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Business name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Telnyx phone number (E.164)</Label>
              <Input
                id="phone"
                value={form.phone_number}
                onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                placeholder="+15551234567"
              />
              <p className="text-xs text-muted-foreground">
                Must match your Telnyx number. Used to route inbound calls to this business.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="escalation">Escalation phone</Label>
              <Input
                id="escalation"
                value={form.escalation_phone}
                onChange={(e) => setForm({ ...form, escalation_phone: e.target.value })}
                placeholder="+15559876543"
              />
              <p className="text-xs text-muted-foreground">
                Calls transfer here when the AI escalates to a human.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Input
                id="timezone"
                value={form.timezone}
                onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                placeholder="America/New_York"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {message && <p className="text-sm text-green-600">{message}</p>}
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save changes"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Telnyx voice setup</CardTitle>
            <CardDescription>
              Create a TeXML Application in Telnyx Mission Control and assign your number
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <p className="font-medium">TeXML webhook URL (GET or POST)</p>
              <code className="mt-1 block rounded bg-muted p-2 text-xs break-all">
                {publicApiUrl}/api/v1/voice/inbound
              </code>
            </div>
            <div>
              <p className="font-medium">Status callback (optional)</p>
              <code className="mt-1 block rounded bg-muted p-2 text-xs break-all">
                {publicApiUrl}/api/v1/voice/status
              </code>
            </div>
            <p className="text-muted-foreground">
              For local dev, expose your API with ngrok and set PUBLIC_API_URL in backend .env.
              Set GROQ_API_KEY and Telnyx credentials (TELNYX_API_KEY, TELNYX_PUBLIC_KEY,
              TELNYX_ACCOUNT_SID) on the backend.
            </p>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
