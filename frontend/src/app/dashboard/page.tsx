"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DashboardShell } from "@/components/dashboard/shell";
import { OnboardingChecklist } from "@/components/dashboard/onboarding-checklist";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import { api, DashboardSummary, formatDate, formatTime } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!getToken()) {
      router.replace("/login");
      return;
    }

    api
      .getDashboard()
      .then(setData)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [authLoading, router]);

  if (authLoading || loading || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading dashboard...</p>
      </div>
    );
  }

  const tz = business?.timezone;

  return (
    <DashboardShell businessName={businessName}>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Your AI receptionist at a glance
          </p>
        </div>

        <OnboardingChecklist />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Today's appointments" value={data.stats.appointments_today} />
          <StatCard title="Open jobs" value={data.stats.jobs_open} />
          <StatCard title="Total customers" value={data.stats.customers_total} />
          <StatCard title="Calls this week" value={data.stats.calls_this_week} />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Today&apos;s appointments</CardTitle>
              <CardDescription>Scheduled visits for today</CardDescription>
            </CardHeader>
            <CardContent>
              {data.today_appointments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No appointments today.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Service</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.today_appointments.map((appt) => (
                      <TableRow key={appt.id}>
                        <TableCell>{formatTime(appt.start_time, tz)}</TableCell>
                        <TableCell>{appt.service_type}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{appt.status}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent conversations</CardTitle>
                <CardDescription>Calls and chats handled by AI</CardDescription>
              </div>
              <Link href="/dashboard/conversations" className="text-sm text-primary hover:underline">
                View inbox
              </Link>
            </CardHeader>
            <CardContent>
              {data.recent_calls.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No calls yet. Configure Telnyx in Settings to enable voice.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>From</TableHead>
                      <TableHead>Summary</TableHead>
                      <TableHead>When</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recent_calls.map((call) => (
                      <TableRow key={call.id}>
                        <TableCell>
                          <Link
                            href={`/dashboard/conversations/${call.id}`}
                            className="hover:underline"
                          >
                            {call.caller_phone ?? "Unknown"}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-xs truncate text-muted-foreground">
                          {call.ai_summary || call.summary || call.status}
                        </TableCell>
                        <TableCell>{formatDate(call.created_at, tz)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent customers</CardTitle>
              <CardDescription>Latest CRM entries</CardDescription>
            </CardHeader>
            <CardContent>
              {data.recent_customers.length === 0 ? (
                <p className="text-sm text-muted-foreground">No customers yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Added</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recent_customers.map((customer) => (
                      <TableRow key={customer.id}>
                        <TableCell>{customer.name}</TableCell>
                        <TableCell>{customer.phone}</TableCell>
                        <TableCell>{formatDate(customer.created_at, tz)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI activity</CardTitle>
              <CardDescription>Tool calls and decisions</CardDescription>
            </CardHeader>
            <CardContent>
              {data.recent_ai_activity.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No AI activity yet. Try the AI Receptionist to test tool calls.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Tool</TableHead>
                      <TableHead>When</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recent_ai_activity.map((activity) => (
                      <TableRow key={activity.id}>
                        <TableCell>{activity.action}</TableCell>
                        <TableCell>{activity.tool_name ?? "—"}</TableCell>
                        <TableCell>{formatDate(activity.created_at, tz)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}
