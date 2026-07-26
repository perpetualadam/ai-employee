"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  ApiError,
  VerificationDocument,
  VerificationRequirements,
  VerificationStatus,
} from "@/lib/api";

const DOCUMENT_LABELS: Record<string, string> = {
  business_registration: "Business registration",
  proof_of_address: "Proof of address",
  id_document: "ID document",
  other: "Other document",
};

type VerificationPanelProps = {
  businessName: string;
  onVerificationUpdated?: () => void;
};

export function VerificationPanel({
  businessName,
  onVerificationUpdated,
}: VerificationPanelProps) {
  const [requirements, setRequirements] = useState<VerificationRequirements | null>(null);
  const [status, setStatus] = useState<VerificationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [address, setAddress] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [req, st] = await Promise.all([
        api.getVerificationRequirements(),
        api.getVerificationStatus(),
      ]);
      setRequirements(req);
      setStatus(st);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load verification status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading verification requirements…</p>;
  }

  if (!requirements?.verification_required) {
    return null;
  }

  const approved = status?.status === "approved" || status?.status === "not_required";
  const submitted = status?.status === "submitted";
  const uploadedTypes = new Set(status?.uploaded_documents.map((d) => d.document_type) ?? []);
  const requiredDocs = requirements.required_documents ?? [];
  const allUploaded = requiredDocs.every((t) => uploadedTypes.has(t));

  async function handleUpload(documentType: string, file: File) {
    setUploading(documentType);
    setError("");
    setSuccess("");
    try {
      await api.uploadVerificationDocument(documentType, file);
      setSuccess("Document uploaded.");
      await load();
      onVerificationUpdated?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(null);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const next = await api.submitVerification({
        business_name: businessName.trim() || "Business",
        contact_email: contactEmail.trim() || undefined,
        address: address.trim() || undefined,
      });
      setStatus(next);
      setSuccess(
        next.status === "approved"
          ? "Verification approved — you can get a phone number now."
          : "Verification submitted — we will enable number search once approved.",
      );
      onVerificationUpdated?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (approved) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm dark:border-green-900 dark:bg-green-950/30">
        <p className="font-medium text-green-800 dark:text-green-200">Regulatory verification approved</p>
        <p className="mt-1 text-green-700 dark:text-green-300">
          You can search for and provision a phone number below.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-lg border bg-muted/20 p-4">
      <div>
        <p className="text-sm font-medium">Regulatory verification required</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {requirements.country_name ?? requirements.country_code} numbers require identity documents
          before provisioning. Upload the files below, then submit for review.
        </p>
      </div>

      {submitted && (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Verification is under review ({status?.status}). Number search unlocks automatically once
          approved — usually within 1–2 business days.
        </p>
      )}

      <ul className="space-y-3">
        {requiredDocs.map((docType) => {
          const uploaded = status?.uploaded_documents.find((d) => d.document_type === docType);
          return (
            <li key={docType} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <div>
                <p className="font-medium">{DOCUMENT_LABELS[docType] ?? docType}</p>
                {uploaded ? (
                  <p className="text-xs text-green-600">Uploaded — {uploaded.verification_status}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">PDF or image, max 10 MB</p>
                )}
              </div>
              {!submitted && (
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf,image/jpeg,image/png"
                    className="sr-only"
                    disabled={uploading !== null}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) void handleUpload(docType, file);
                      e.target.value = "";
                    }}
                  />
                  <Button type="button" variant="outline" size="sm" asChild>
                    <span>{uploading === docType ? "Uploading…" : uploaded ? "Replace" : "Upload"}</span>
                  </Button>
                </label>
              )}
            </li>
          );
        })}
      </ul>

      {!submitted && (
        <div className="space-y-3 border-t pt-4">
          <div className="space-y-2">
            <Label htmlFor="verify-email">Contact email (optional)</Label>
            <Input
              id="verify-email"
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="owner@yourbusiness.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="verify-address">Business address (optional)</Label>
            <Input
              id="verify-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Street, city, postcode"
            />
          </div>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || !allUploaded}
          >
            {submitting ? "Submitting…" : "Submit for verification"}
          </Button>
          {!allUploaded && (
            <p className="text-xs text-muted-foreground">Upload all required documents before submitting.</p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
      {success && <p className="text-sm text-green-600">{success}</p>}
    </div>
  );
}
