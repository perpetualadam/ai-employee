import type { LucideIcon } from "lucide-react";
import {
  Bot,
  CalendarDays,
  CreditCard,
  Inbox,
  LayoutDashboard,
  Settings,
  Users,
  Wrench,
} from "lucide-react";

export interface DashboardNavItem {
  href: string;
  label: string;
  shortLabel?: string;
  icon: LucideIcon;
  /** Show in mobile bottom bar */
  mobilePrimary?: boolean;
}

export const dashboardNavItems: DashboardNavItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    shortLabel: "Home",
    icon: LayoutDashboard,
    mobilePrimary: true,
  },
  {
    href: "/dashboard/conversations",
    label: "Inbox",
    icon: Inbox,
    mobilePrimary: true,
  },
  {
    href: "/dashboard/receptionist",
    label: "AI Receptionist",
    shortLabel: "AI Chat",
    icon: Bot,
  },
  {
    href: "/dashboard/customers",
    label: "Customers",
    icon: Users,
    mobilePrimary: true,
  },
  {
    href: "/dashboard/jobs",
    label: "Jobs",
    icon: Wrench,
  },
  {
    href: "/dashboard/calendar",
    label: "Calendar",
    icon: CalendarDays,
    mobilePrimary: true,
  },
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: Settings,
  },
  {
    href: "/dashboard/billing",
    label: "Billing",
    icon: CreditCard,
  },
];

export const mobilePrimaryNavItems = dashboardNavItems.filter(
  (item) => item.mobilePrimary,
);

export function isNavItemActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") {
    return pathname === "/dashboard";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
