import Link from "next/link";
import {
  Calendar,
  MessageSquare,
  Phone,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";

const highlights = [
  {
    icon: Phone,
    title: "Answers every call",
    description: "24/7 on your business line with trade-specific intake.",
  },
  {
    icon: Calendar,
    title: "Books real jobs",
    description: "Checks your calendar and updates your CRM automatically.",
  },
  {
    icon: MessageSquare,
    title: "Escalates when needed",
    description: "Transfers urgent calls or notifies you by SMS and email.",
  },
];

interface AuthShellProps {
  children: React.ReactNode;
  title: string;
  description: string;
  footer: React.ReactNode;
}

export function AuthShell({ children, title, description, footer }: AuthShellProps) {
  return (
    <div className="dashboard-mesh min-h-screen">
      <div className="grid min-h-screen lg:grid-cols-2">
        <aside className="relative hidden flex-col justify-between border-r border-border/80 bg-sidebar p-10 lg:flex">
          <div>
            <Link href="/" className="inline-flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <Sparkles className="size-5" aria-hidden />
              </div>
              <span className="font-heading text-lg font-semibold">AI Employee</span>
            </Link>
            <p className="mt-10 max-w-md text-lg leading-relaxed text-muted-foreground">
              Your AI receptionist for trade businesses — answer calls, book jobs, and
              never miss a lead.
            </p>
          </div>

          <ul className="space-y-5">
            {highlights.map((item) => (
              <li key={item.title} className="flex gap-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <item.icon className="size-5" aria-hidden />
                </div>
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-sm text-muted-foreground">{item.description}</p>
                </div>
              </li>
            ))}
          </ul>

          <p className="text-xs text-muted-foreground">
            14-day free trial · No credit card to start
          </p>
        </aside>

        <div className="flex flex-col">
          <header className="flex items-center justify-between border-b border-border/80 px-4 py-4 sm:px-6 lg:border-none lg:justify-end">
            <Link href="/" className="inline-flex items-center gap-2 lg:hidden">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="size-4" aria-hidden />
              </div>
              <span className="font-semibold">AI Employee</span>
            </Link>
            <Link
              href="/"
              className="hidden text-sm text-muted-foreground hover:text-foreground lg:inline"
            >
              ← Back to home
            </Link>
          </header>

          <main className="flex flex-1 items-center justify-center px-4 py-8 sm:px-6">
            <div className="w-full max-w-md animate-in fade-in duration-300">
              <div className="mb-6 space-y-2 text-center lg:text-left">
                <h1 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
                  {title}
                </h1>
                <p className="text-sm text-muted-foreground sm:text-base">
                  {description}
                </p>
              </div>

              <div
                className={cn(
                  "rounded-xl border border-border/80 bg-card p-6 shadow-sm sm:p-8",
                )}
              >
                {children}
              </div>

              <div className="mt-6 text-center text-sm text-muted-foreground">
                {footer}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
