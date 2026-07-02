"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  ApiError,
  AvailablePhoneNumber,
  Business,
  PhoneProvisioningStatus,
} from "@/lib/api";

type PhoneProvisioningPanelProps = {
  business: Business | null;
  onPhoneUpdated: (business: Business) => void;
  /** Hide manual entry when onboarding should force provision/search first */
  compact?: boolean;
};

export function PhoneProvisioningPanel({
  business,
  onPhoneUpdated,
  compact = false,
}: PhoneProvisioningPanelProps) {
  const [status, setStatus] = useState<PhoneProvisioningStatus | null>(null);
  const [areaCode, setAreaCode] = useState("");
  const [results, setResults] = useState<AvailablePhoneNumber[]>([]);
  const [manualPhone, setManualPhone] = useState(business?.phone_number ?? "");
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [searching, setSearching] = useState(false);
  const [provisioning, setProvisioning] = useState<string | null>(null);
  const [savingManual, setSavingManual] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    setError("");
    try {
      const next = await api.getPhoneProvisioningStatus();
      setStatus(next);
      if (next.phone_number) {
        setManualPhone(next.phone_number);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load phone status");
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus, business?.phone_number]);

  async function handleSearch() {
    setSearching(true);
    setError("");
    setSuccess("");
    setResults([]);
    try {
      const data = await api.searchAvailablePhoneNumbers(areaCode.trim() || undefined);
      setResults(data.numbers);
      if (data.numbers.length === 0) {
        setError("No numbers found — try a different area code.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function handleProvision(phoneNumber: string) {
    setProvisioning(phoneNumber);
    setError("");
    setSuccess("");
    try {
      const result = await api.provisionPhoneNumber(phoneNumber);
      setSuccess(result.message);
      const updated = await api.getBusiness();
      onPhoneUpdated(updated);
      await loadStatus();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not provision number");
    } finally {
      setProvisioning(null);
    }
  }

  async function handleManualSave() {
    setSavingManual(true);
    setError("");
    setSuccess("");
    try {
      const updated = await api.updateBusiness({ phone_number: manualPhone.trim() });
      onPhoneUpdated(updated);
      setSuccess("Phone number saved.");
      await loadStatus();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save phone number");
    } finally {
      setSavingManual(false);
    }
  }

  if (loadingStatus) {
    return <p className="text-sm text-muted-foreground">Loading phone setup…</p>;
  }

  if (status?.provisioned && status.phone_number) {
    return (
      <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
        <div>
          <p className="text-sm font-medium">Your business line</p>
          <p className="text-lg font-semibold tracking-tight">{status.phone_number}</p>
        </div>
        <p className="text-xs text-muted-foreground">
          Provisioned automatically — inbound calls route to your AI receptionist. Voice and SMS
          are configured on this number.
        </p>
        {success && <p className="text-sm text-green-600">{success}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {status?.can_search ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Search for a local number in {status.country}. We&apos;ll buy it, connect voice + SMS,
            and assign it to your AI receptionist — no Telnyx dashboard required.
          </p>
          <div className="flex flex-wrap gap-2">
            <div className="flex-1 min-w-[140px] space-y-1">
              <Label htmlFor="area-code">Area code (optional)</Label>
              <Input
                id="area-code"
                value={areaCode}
                onChange={(e) => setAreaCode(e.target.value.replace(/\D/g, "").slice(0, 10))}
                placeholder="614"
              />
            </div>
            <div className="flex items-end">
              <Button type="button" variant="secondary" onClick={handleSearch} disabled={searching}>
                {searching ? "Searching…" : "Search numbers"}
              </Button>
            </div>
          </div>
          {results.length > 0 && (
            <ul className="divide-y rounded-lg border">
              {results.map((item) => (
                <li
                  key={item.phone_number}
                  className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm"
                >
                  <div>
                    <p className="font-medium">{item.phone_number}</p>
                    {item.region && (
                      <p className="text-xs text-muted-foreground">{item.region}</p>
                    )}
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleProvision(item.phone_number)}
                    disabled={provisioning !== null}
                  >
                    {provisioning === item.phone_number ? "Setting up…" : "Get this number"}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        !compact && (
          <p className="text-sm text-muted-foreground">
            Automatic provisioning is not enabled on this platform. Enter a number you already
            own in Telnyx below — it must use the shared TeXML webhook from Settings.
          </p>
        )
      )}

      {status?.manual_fallback_allowed && (
        <div className="space-y-2 border-t pt-4">
          <Label htmlFor="manual-phone">
            {status.can_search ? "Or enter your own Telnyx number" : "Telnyx phone number (E.164)"}
          </Label>
          <Input
            id="manual-phone"
            value={manualPhone}
            onChange={(e) => setManualPhone(e.target.value)}
            placeholder="+15551234567"
          />
          <Button
            type="button"
            variant="outline"
            onClick={handleManualSave}
            disabled={savingManual || !manualPhone.trim()}
          >
            {savingManual ? "Saving…" : "Save phone number"}
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
      {success && <p className="text-sm text-green-600">{success}</p>}
    </div>
  );
}
