"use client";

import Link from "next/link";
import { Check, Circle } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, OnboardingStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

export function OnboardingChecklist() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    api
      .getOnboardingStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !status || status.onboarding_completed) {
    return null;
  }

  async function handleSampleData() {
    setSeeding(true);
    try {
      await api.seedSampleData();
      window.location.reload();
    } finally {
      setSeeding(false);
    }
  }

  return (
    <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 via-background to-accent/30">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Get your AI receptionist live</CardTitle>
            <CardDescription>
              {status.completed_count} of {status.total_steps} steps complete
            </CardDescription>
          </div>
          <Badge variant="secondary">{status.progress_percent}%</Badge>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${status.progress_percent}%` }}
            role="progressbar"
            aria-valuenow={status.progress_percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Onboarding progress"
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {status.steps.map((step) => (
          <Link
            key={step.id}
            href={step.href}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-3 transition-all hover:border-primary/30 hover:bg-background/80 hover:shadow-sm",
              step.completed && "border-success/30 bg-success/5",
            )}
          >
            <span
              className={cn(
                "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full",
                step.completed
                  ? "bg-success text-success-foreground"
                  : "border-2 border-muted-foreground/30 text-transparent",
              )}
              aria-hidden
            >
              {step.completed ? (
                <Check className="size-3.5" />
              ) : (
                <Circle className="size-3.5 text-muted-foreground/40" />
              )}
            </span>
            <div>
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-xs text-muted-foreground">{step.description}</p>
            </div>
          </Link>
        ))}

        <div className="flex flex-wrap gap-3 pt-3">
          <Link href="/onboarding" className={buttonVariants({ size: "sm" })}>
            Continue setup
          </Link>
          <button
            type="button"
            className={buttonVariants({ variant: "outline", size: "sm" })}
            onClick={handleSampleData}
            disabled={seeding}
          >
            {seeding ? "Adding..." : "Load sample data"}
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
