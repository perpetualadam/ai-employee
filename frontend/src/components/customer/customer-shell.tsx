import Link from "next/link";
import { AlertCircle, Sparkles } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function businessInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

interface CustomerShellProps {
  businessName: string;
  description?: string;
  badge?: string;
  children: React.ReactNode;
  className?: string;
  compact?: boolean;
}

export function CustomerShell({
  businessName,
  description,
  badge,
  children,
  className,
  compact = false,
}: CustomerShellProps) {
  return (
    <div className="dashboard-mesh flex min-h-[100dvh] flex-col">
      <header className="border-b border-border/80 bg-background/90 backdrop-blur-md">
        <div
          className={cn(
            "mx-auto flex h-16 items-center gap-3 px-4",
            compact ? "max-w-lg" : "max-w-2xl",
          )}
        >
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground shadow-sm">
            {businessInitials(businessName)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-heading text-sm font-semibold">{businessName}</p>
            {description && (
              <p className="truncate text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          {badge && (
            <span className="hidden rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary sm:inline">
              {badge}
            </span>
          )}
        </div>
      </header>

      <main
        className={cn(
          "mx-auto flex w-full flex-1 flex-col px-4 py-4 sm:py-6",
          compact ? "max-w-lg" : "max-w-2xl",
          className,
        )}
      >
        {children}
      </main>

      <footer className="border-t border-border/60 bg-background/80 py-3 text-center">
        <p className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="size-3" aria-hidden />
          Powered by{" "}
          <Link href="/" className="font-medium text-foreground hover:text-primary">
            AI Employee
          </Link>
        </p>
      </footer>
    </div>
  );
}

export function CustomerChatSkeleton() {
  return (
    <div className="dashboard-mesh flex min-h-[100dvh] flex-col">
      <div className="border-b border-border/80 bg-background/90 px-4 py-4">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <Skeleton className="size-10 rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-52" />
          </div>
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4 p-4">
        <Skeleton className="min-h-[420px] flex-1 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
      </div>
    </div>
  );
}

export function CustomerFormSkeleton() {
  return (
    <div className="dashboard-mesh flex min-h-[100dvh] items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
    </div>
  );
}

interface CustomerErrorStateProps {
  title?: string;
  message: string;
  actionLabel?: string;
  actionHref?: string;
}

export function CustomerErrorState({
  title = "Something went wrong",
  message,
  actionLabel = "Go to homepage",
  actionHref = "/",
}: CustomerErrorStateProps) {
  return (
    <div className="dashboard-mesh flex min-h-[100dvh] items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-border/80 bg-card p-8 text-center shadow-sm animate-in fade-in duration-300">
        <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" aria-hidden />
        </div>
        <h1 className="font-heading text-lg font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
        {actionHref && (
          <Link
            href={actionHref}
            className={cn(buttonVariants({ variant: "outline" }), "mt-6 inline-flex")}
          >
            {actionLabel}
          </Link>
        )}
      </div>
    </div>
  );
}
