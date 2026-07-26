"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DashboardShell } from "@/components/dashboard/shell";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import {
  api,
  ConversationListItem,
  formatDate,
  formatDateTime,
} from "@/lib/api";

function LeadCardPreview({ lead }: { lead: ConversationListItem["lead_card"] }) {
  return (
    <div className="mt-2 space-y-1 text-sm text-muted-foreground">
      {lead.customer_name && <p><span className="font-medium text-foreground">Name:</span> {lead.customer_name}</p>}
      {lead.service_type && <p><span className="font-medium text-foreground">Need:</span> {lead.service_type}</p>}
      {lead.service_address && <p><span className="font-medium text-foreground">Address:</span> {lead.service_address}</p>}
      {lead.appointment_time && (
        <p><span className="font-medium text-foreground">Appointment:</span> {formatDateTime(lead.appointment_time)}</p>
      )}
    </div>
  );
}

export default function ConversationsPage() {
  const router = useRouter();
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [items, setItems] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    api
      .listConversations()
      .then(setItems)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [authLoading, router]);

  const tz = business?.timezone;

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading inbox...</p>
      </div>
    );
  }

  return (
    <DashboardShell businessName={businessName}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Inbox</h1>
          <p className="text-muted-foreground">
            Calls, texts, and AI summaries in one timeline
          </p>
        </div>

        {items.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No customer conversations yet. Calls and chat sessions will appear here.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {items.map((item) => (
              <Link key={item.id} href={`/dashboard/conversations/${item.id}`}>
                <Card className="transition-colors hover:bg-muted/40">
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle className="text-base">
                        {item.lead_card.customer_name || item.caller_phone || "Unknown caller"}
                      </CardTitle>
                      <Badge variant="secondary">{item.channel_label}</Badge>
                      {item.lead_card.is_booked && <Badge>Booked</Badge>}
                      {item.lead_card.is_emergency && <Badge variant="destructive">Urgent</Badge>}
                      {item.escalated && <Badge variant="destructive">Escalated</Badge>}
                    </div>
                    <CardDescription>{formatDate(item.created_at, tz)}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {item.ai_summary ? (
                      <p className="text-sm">{item.ai_summary}</p>
                    ) : (
                      <p className="text-sm text-muted-foreground">{item.summary || "In progress"}</p>
                    )}
                    <LeadCardPreview lead={item.lead_card} />
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
