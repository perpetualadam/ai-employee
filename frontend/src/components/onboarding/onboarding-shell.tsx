import Link from "next/link";
import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

interface OnboardingShellProps {
  children: React.ReactNode;
  skipHref?: string;
  skipLabel?: string;
}

export function OnboardingShell({
  children,
  skipHref = "/dashboard",
  skipLabel = "Skip for now",
}: OnboardingShellProps) {
  return (
    <div className="dashboard-mesh min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4 sm:px-6">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Sparkles className="size-4" aria-hidden />
            </div>
            <div>
              <p className="text-sm font-semibold leading-none">AI Employee</p>
              <p className="text-xs text-muted-foreground">Setup wizard</p>
            </div>
          </Link>
          <Link
            href={skipHref}
            className={cn(
              "text-sm text-muted-foreground transition-colors hover:text-foreground",
            )}
          >
            {skipLabel}
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
        {children}
      </main>
    </div>
  );
}
