"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useDashboardAuth } from "@/components/dashboard/dashboard-auth-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
  dashboardNavItems,
  isNavItemActive,
  mobilePrimaryNavItems,
} from "@/lib/dashboard-nav";
import { cn } from "@/lib/utils";

function businessInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "AI";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
  onNavigate,
  compact,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  onNavigate?: () => void;
  compact?: boolean;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
        compact && "flex-col gap-1 px-2 py-2 text-[0.7rem]",
        active
          ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
          : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
      )}
    >
      <Icon
        className={cn(
          "size-4 shrink-0",
          compact && "size-5",
          active ? "opacity-100" : "opacity-70 group-hover:opacity-100",
        )}
        aria-hidden
      />
      <span className={cn(compact && "leading-tight")}>{label}</span>
    </Link>
  );
}

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { businessName, loading } = useDashboardAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNavOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileNavOpen]);

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // Cookie may already be cleared; still redirect.
    }
    router.push("/login");
  }

  return (
    <div className="dashboard-mesh min-h-screen bg-background">
      <a
        href="#dashboard-main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              className="md:hidden"
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-nav-drawer"
              aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
              onClick={() => setMobileNavOpen((open) => !open)}
            >
              {mobileNavOpen ? <X /> : <Menu />}
            </Button>
            <Link href="/dashboard" className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <Sparkles className="size-5" aria-hidden />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold leading-none">
                  AI Employee
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {loading ? "Loading..." : businessName}
                </p>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <Avatar size="sm" className="hidden sm:flex">
              <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                {businessInitials(businessName)}
              </AvatarFallback>
            </Avatar>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="hidden sm:inline-flex"
            >
              Sign out
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={handleLogout}
              className="sm:hidden"
              aria-label="Sign out"
            >
              <LogOut />
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 pb-24 sm:px-6 md:gap-8 md:py-8 md:pb-8">
        <aside
          aria-label="Dashboard navigation"
          className="hidden w-56 shrink-0 md:block"
        >
          <nav className="sticky top-24 space-y-1 rounded-xl border border-sidebar-border bg-sidebar p-2 shadow-sm">
            {dashboardNavItems.map((item) => (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                icon={item.icon}
                active={isNavItemActive(pathname, item.href)}
              />
            ))}
          </nav>
        </aside>

        <main
          id="dashboard-main"
          className="min-w-0 flex-1 focus:outline-none"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>

      <nav
        aria-label="Mobile primary navigation"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur-md md:hidden"
      >
        <div className="mx-auto grid max-w-lg grid-cols-5 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2">
          {mobilePrimaryNavItems.map((item) => (
            <NavLink
              key={item.href}
              href={item.href}
              label={item.shortLabel ?? item.label}
              icon={item.icon}
              active={isNavItemActive(pathname, item.href)}
              compact
            />
          ))}
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            className={cn(
              "group flex flex-col items-center gap-1 rounded-lg px-2 py-2 text-[0.7rem] font-medium transition-all",
              mobileNavOpen
                ? "bg-sidebar-primary text-sidebar-primary-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-nav-drawer"
          >
            <Menu className="size-5 opacity-70 group-hover:opacity-100" aria-hidden />
            <span>More</span>
          </button>
        </div>
      </nav>

      {mobileNavOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-50 bg-foreground/20 backdrop-blur-[2px] md:hidden"
            aria-label="Close navigation menu"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside
            id="mobile-nav-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Full navigation menu"
            className="fixed inset-y-0 left-0 z-50 flex w-[min(100%,18rem)] flex-col border-r border-sidebar-border bg-sidebar shadow-xl animate-in slide-in-from-left duration-200 md:hidden"
          >
            <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-4">
              <div>
                <p className="text-sm font-semibold">Navigation</p>
                <p className="text-xs text-muted-foreground">{businessName}</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Close menu"
                onClick={() => setMobileNavOpen(false)}
              >
                <X />
              </Button>
            </div>
            <nav className="flex-1 space-y-1 overflow-y-auto p-3">
              {dashboardNavItems.map((item) => (
                <NavLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={isNavItemActive(pathname, item.href)}
                  onNavigate={() => setMobileNavOpen(false)}
                />
              ))}
            </nav>
          </aside>
        </>
      )}
    </div>
  );
}
