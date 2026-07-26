"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

const SERVICE_LABELS: Record<string, string> = {
  telephony: "Telephony (calls)",
  numbers: "Phone numbers",
  regulatory: "Regulatory / KYC",
  voice: "Voice AI",
  messaging: "Messaging (SMS/email)",
  storage: "Document storage",
};

type ProviderSettings = {
  provider_config: Record<string, string>;
  country_defaults: Record<string, string>;
  global_defaults: Record<string, string>;
  available: Record<string, string[]>;
};

type ProviderConfigPanelProps = {
  country: string;
  onSaved?: () => void;
};

export function ProviderConfigPanel({ country, onSaved }: ProviderConfigPanelProps) {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getProviderSettings();
      setSettings(data);
      setDraft({});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load provider settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function effectiveValue(service: string): string {
    if (service in draft) {
      return draft[service];
    }
    return settings?.provider_config[service] ?? "";
  }

  function defaultLabel(service: string): string {
    const countryDefault = settings?.country_defaults[service];
    const globalDefault = settings?.global_defaults[service];
    const value = countryDefault ?? globalDefault ?? "platform default";
    return `Default for ${country}: ${value}`;
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const provider_config: Record<string, string> = {};
      for (const [service, value] of Object.entries(draft)) {
        provider_config[service] = value;
      }
      await api.updateBusiness({ provider_config });
      setMessage("Provider settings saved.");
      await load();
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save provider settings");
    } finally {
      setSaving(false);
    }
  }

  const services = settings ? Object.keys(settings.available).sort() : [];
  const hasDraftChanges = Object.keys(draft).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Telecom providers</CardTitle>
        <CardDescription>
          Override which provider handles each service for this business. Leave on &quot;Use
          default&quot; to follow country configuration ({country}).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading provider options…</p>
        ) : settings ? (
          <>
            {services.map((service) => (
              <div key={service} className="space-y-2">
                <Label htmlFor={`provider-${service}`}>
                  {SERVICE_LABELS[service] ?? service}
                </Label>
                <select
                  id={`provider-${service}`}
                  value={effectiveValue(service)}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      [service]: e.target.value,
                    }))
                  }
                  className="h-9 w-full rounded-lg border border-input bg-background px-2 text-sm"
                >
                  <option value="">Use default ({defaultLabel(service)})</option>
                  {(settings.available[service] ?? []).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                {settings.provider_config[service] && !(service in draft) ? (
                  <p className="text-xs text-muted-foreground">
                    Active override: {settings.provider_config[service]}
                  </p>
                ) : null}
              </div>
            ))}
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {message ? <p className="text-sm text-green-600">{message}</p> : null}
            <Button onClick={handleSave} disabled={saving || !hasDraftChanges}>
              {saving ? "Saving…" : "Save provider settings"}
            </Button>
          </>
        ) : (
          <p className="text-sm text-destructive">{error || "Unable to load provider settings."}</p>
        )}
      </CardContent>
    </Card>
  );
}
