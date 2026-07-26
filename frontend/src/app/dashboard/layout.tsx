"use client";

import { DashboardAuthProvider } from "@/components/dashboard/dashboard-auth-provider";
import { DashboardShell } from "@/components/dashboard/shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardAuthProvider>
      <DashboardShell>{children}</DashboardShell>
    </DashboardAuthProvider>
  );
}
