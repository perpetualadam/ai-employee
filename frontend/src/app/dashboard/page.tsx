"use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CalendarDays,
  Inbox,
  Phone,
  Users,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/dashboard/empty-state";
import { OnboardingChecklist } from "@/components/dashboard/onboarding-checklist";
import { PageHeader } from "@/components/dashboard/page-header";
import { DashboardOverviewSkeleton } from "@/components/dashboard/page-skeletons";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
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

export default function DashboardPage() {
  const router = useRouter();
  const { business, loading: authLoading } = useDashboardAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;

    api
      .getDashboard()
      .then(setData)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [authLoading, router]);

  if (authLoading || loading || !data) {
    return <DashboardOverviewSkeleton />;
  }

  const tz = business?.timezone;
  const firstName = business?.name?.split(/\s+/)[0] ?? "there";

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <PageHeader
        title={`Good ${getGreeting()}, ${firstName}`}
        description="Your AI receptionist at a glance — appointments, leads, and activity."
        actions={
          <Link
            href="/dashboard/receptionist"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Test AI receptionist
            <ArrowRight className="size-4" />
          </Link>
        }
      />

      <OnboardingChecklist />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Today's appointments"
          value={data.stats.appointments_today}
          icon={CalendarDays}
          tone="primary"
        />
        <StatCard
          title="Open jobs"
          value={data.stats.jobs_open}
          icon={Wrench}
          tone="warning"
        />
        <StatCard
          title="Total customers"
          value={data.stats.customers_total}
          icon={Users}
          tone="success"
        />
        <StatCard
          title="Calls this week"
          value={data.stats.calls_this_week}
          icon={Phone}
          tone="default"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DashboardPanel
          title="Today's appointments"
          description="Scheduled visits for today"
          empty={
            <EmptyState
              icon={CalendarDays}
              title="No appointments today"
              description="When customers book through your AI receptionist, they'll show up here."
              actionLabel="Open calendar"
              actionHref="/dashboard/calendar"
            />
          }
          isEmpty={data.today_appointments.length === 0}
        >
          <div className="overflow-x-auto -mx-2 px-2">
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
                    <TableCell className="font-medium">
                      {formatTime(appt.start_time, tz)}
                    </TableCell>
                    <TableCell>{appt.service_type}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{appt.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DashboardPanel>

        <DashboardPanel
          title="Recent conversations"
          description="Calls and chats handled by AI"
          action={
            <Link
              href="/dashboard/conversations"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              View inbox
              <ArrowRight className="size-3.5" />
            </Link>
          }
          empty={
            <EmptyState
              icon={Inbox}
              title="No conversations yet"
              description="Configure your phone number in Settings to start receiving calls and messages."
              actionLabel="Go to settings"
              actionHref="/dashboard/settings"
            />
          }
          isEmpty={data.recent_calls.length === 0}
        >
          <div className="overflow-x-auto -mx-2 px-2">
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
                        className="font-medium hover:text-primary hover:underline"
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
          </div>
        </DashboardPanel>

        <DashboardPanel
          title="Recent customers"
          description="Latest CRM entries"
          action={
            <Link
              href="/dashboard/customers"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              View all
              <ArrowRight className="size-3.5" />
            </Link>
          }
          empty={
            <EmptyState
              icon={Users}
              title="No customers yet"
              description="Customers are added automatically when your AI receptionist captures their details."
              actionLabel="Add customer"
              actionHref="/dashboard/customers"
            />
          }
          isEmpty={data.recent_customers.length === 0}
        >
          <div className="overflow-x-auto -mx-2 px-2">
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
                    <TableCell className="font-medium">{customer.name}</TableCell>
                    <TableCell>{customer.phone}</TableCell>
                    <TableCell>{formatDate(customer.created_at, tz)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DashboardPanel>

        <DashboardPanel
          title="AI activity"
          description="Tool calls and decisions"
          empty={
            <EmptyState
              icon={Bot}
              title="No AI activity yet"
              description="Try the AI Receptionist chat to see how your assistant handles customer requests."
              actionLabel="Open AI receptionist"
              actionHref="/dashboard/receptionist"
            />
          }
          isEmpty={data.recent_ai_activity.length === 0}
        >
          <div className="overflow-x-auto -mx-2 px-2">
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
          </div>
        </DashboardPanel>
      </div>
    </div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

function DashboardPanel({
  title,
  description,
  action,
  children,
  empty,
  isEmpty,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  empty: React.ReactNode;
  isEmpty: boolean;
}) {
  return (
    <Card className="transition-shadow hover:shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        {action}
      </CardHeader>
      <CardContent>{isEmpty ? empty : children}</CardContent>
    </Card>
  );
}
