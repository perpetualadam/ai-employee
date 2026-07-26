"use client";

import { useEffect, useMemo, useState } from "react";

import { CopySnippet } from "@/components/copy-snippet";
import { DashboardShell } from "@/components/dashboard/shell";
import { PhoneProvisioningPanel } from "@/components/phone-provisioning-panel";
import { ProviderConfigPanel } from "@/components/provider-config-panel";
import { TimezoneSelect } from "@/components/timezone-select";
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
  const { businessName, business, loading: authLoading, refreshBusiness } = useDashboardAuth();
  const [form, setForm] = useState({
    name: "",
    escalation_phone: "",
    timezone: "",
    reminders_enabled: true,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [chatOrigin, setChatOrigin] = useState("");
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");

  useEffect(() => {
    setChatOrigin(window.location.origin);
  }, []);

  useEffect(() => {
    if (business) {
      setForm({
        name: business.name,
        escalation_phone: business.escalation_phone ?? "",
        timezone: business.timezone,
        reminders_enabled: business.reminders_enabled ?? true,
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
        escalation_phone: form.escalation_phone || undefined,
        timezone: form.timezone,
        reminders_enabled: form.reminders_enabled,
      });
      setMessage("Settings saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleExportData() {
    setExporting(true);
    setError("");
    setMessage("");
    try {
      const payload = await api.exportAccountData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ai-employee-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Account data export downloaded.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleDeleteAccount() {
    if (deleteConfirmation !== "DELETE") {
      setError('Type DELETE in the confirmation box to permanently delete your account.');
      return;
    }
    setDeleting(true);
    setError("");
    setMessage("");
    try {
      await api.deleteAccount("DELETE");
      window.location.href = "/login";
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Account deletion failed");
    } finally {
      setDeleting(false);
    }
  }

  const publicApiUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? "http://localhost:8000";

  const publicChatUrl = business?.public_slug
    ? `${chatOrigin || ""}/chat/${business.public_slug}`
    : "";

  const websiteButtonSnippet = useMemo(() => {
    if (!publicChatUrl) return "";
    const label = business?.name ? `Chat with ${business.name}` : "Chat with us";
    return `<a href="${publicChatUrl}" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:12px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;font-family:sans-serif;font-weight:600;">${label}</a>`;
  }, [publicChatUrl, business?.name]);

  const websiteEmbedSnippet = useMemo(() => {
    if (!publicChatUrl) return "";
    const title = business?.name ?? "Customer chat";
    return `<iframe src="${publicChatUrl}" title="${title.replace(/"/g, "&quot;")}" style="width:100%;max-width:420px;height:640px;border:1px solid #e5e7eb;border-radius:8px;" loading="lazy"></iframe>`;
  }, [publicChatUrl, business?.name]);

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
            <TimezoneSelect
              value={form.timezone}
              onChange={(timezone) => setForm({ ...form, timezone })}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.reminders_enabled}
                onChange={(e) =>
                  setForm({ ...form, reminders_enabled: e.target.checked })
                }
              />
              Send automatic appointment reminders (~24 hours before)
            </label>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {message && <p className="text-sm text-green-600">{message}</p>}
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save changes"}
            </Button>
          </CardContent>
        </Card>

        {business ? (
          <ProviderConfigPanel
            country={business.country}
            onSaved={async () => {
              await refreshBusiness();
            }}
          />
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Business phone line</CardTitle>
            <CardDescription>
              Search and provision a number, or connect one you already own in Telnyx
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PhoneProvisioningPanel
              business={business}
              onPhoneUpdated={async () => {
                await refreshBusiness();
                setMessage("Phone number updated.");
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Customer web chat</CardTitle>
            <CardDescription>
              Share this link on your website, Google Business, or QR code — customers can book
              without calling
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 text-sm">
            {business?.public_slug ? (
              chatOrigin ? (
                <>
                  <CopySnippet
                    label="Public chat URL"
                    value={publicChatUrl}
                    description="Paste this link on your website, Google Business profile, or QR code."
                  />
                  <CopySnippet
                    label="Website button (HTML)"
                    value={websiteButtonSnippet}
                    description="Adds a “Chat with us” button that opens your receptionist in a new tab."
                    multiline
                  />
                  <CopySnippet
                    label="Embedded chat (HTML)"
                    value={websiteEmbedSnippet}
                    description="Embeds the chat window directly on a page on your site."
                    multiline
                  />
                  <p className="text-muted-foreground">
                    During a call, the AI can also send a continue link so customers finish intake
                    online (voice handoff).
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">Loading your chat link…</p>
              )
            ) : (
              <p className="text-muted-foreground">
                Save your business profile to generate your public chat link.
              </p>
            )}
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

        <Card>
          <CardHeader>
            <CardTitle>Privacy &amp; data</CardTitle>
            <CardDescription>
              Export your account data or permanently delete your account and business data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={handleExportData} disabled={exporting}>
                {exporting ? "Preparing export…" : "Download my data"}
              </Button>
            </div>
            <div className="space-y-2 rounded-lg border border-destructive/30 p-4">
              <p className="text-sm font-medium text-destructive">Delete account</p>
              <p className="text-sm text-muted-foreground">
                This permanently removes your user account, business profile, customers, jobs,
                conversations, and related records. This cannot be undone.
              </p>
              <Label htmlFor="delete-confirmation">Type DELETE to confirm</Label>
              <Input
                id="delete-confirmation"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                placeholder="DELETE"
              />
              <Button variant="destructive" onClick={handleDeleteAccount} disabled={deleting}>
                {deleting ? "Deleting…" : "Delete my account"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  );
}
