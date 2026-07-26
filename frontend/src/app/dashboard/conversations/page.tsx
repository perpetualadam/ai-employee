"use client";

import Link from "next/link";
import { Inbox, MessageSquare, Phone } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
import { InboxSkeleton } from "@/components/dashboard/page-skeletons";
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
import { cn } from "@/lib/utils";

function LeadCardPreview({ lead }: { lead: ConversationListItem["lead_card"] }) {
  return (
    <div className="mt-3 grid gap-1 text-sm text-muted-foreground sm:grid-cols-2">
      {lead.customer_name && (
        <p>
          <span className="font-medium text-foreground">Name:</span>{" "}
          {lead.customer_name}
        </p>
      )}
      {lead.service_type && (
        <p>
          <span className="font-medium text-foreground">Need:</span>{" "}
          {lead.service_type}
        </p>
      )}
      {lead.service_address && (
        <p className="sm:col-span-2">
          <span className="font-medium text-foreground">Address:</span>{" "}
          {lead.service_address}
        </p>
      )}
      {lead.appointment_time && (
        <p>
          <span className="font-medium text-foreground">Appointment:</span>{" "}
          {formatDateTime(lead.appointment_time)}
        </p>
      )}
    </div>
  );
}

function channelIcon(channel: string) {
  if (channel.toLowerCase().includes("call")) return Phone;
  return MessageSquare;
}

export default function ConversationsPage() {
  const router = useRouter();
  const { business, loading: authLoading } = useDashboardAuth();
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
    return <InboxSkeleton />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <PageHeader
        title="Inbox"
        description="Calls, texts, and AI summaries in one timeline"
      />

      {items.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Your inbox is empty"
          description="When customers call or chat, conversations will appear here with AI summaries and lead details."
          actionLabel="Configure phone"
          actionHref="/dashboard/settings"
        />
      ) : (
        <div className="grid gap-3">
          {items.map((item) => {
            const ChannelIcon = channelIcon(item.channel_label);
            return (
              <Link
                key={item.id}
                href={`/dashboard/conversations/${item.id}`}
                className="group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Card
                  className={cn(
                    "transition-all hover:border-primary/30 hover:shadow-md",
                    item.escalated && "border-destructive/30",
                  )}
                >
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex min-w-0 items-start gap-3">
                        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                          <ChannelIcon className="size-4" aria-hidden />
                        </div>
                        <div className="min-w-0">
                          <CardTitle className="truncate text-base">
                            {item.lead_card.customer_name ||
                              item.caller_phone ||
                              "Unknown caller"}
                          </CardTitle>
                          <CardDescription>
                            {formatDate(item.created_at, tz)}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant="secondary">{item.channel_label}</Badge>
                        {item.lead_card.is_booked && <Badge>Booked</Badge>}
                        {item.lead_card.is_emergency && (
                          <Badge variant="destructive">Urgent</Badge>
                        )}
                        {item.escalated && (
                          <Badge variant="destructive">Escalated</Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {item.ai_summary ? (
                      <p className="text-sm leading-relaxed">{item.ai_summary}</p>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        {item.summary || "In progress"}
                      </p>
                    )}
                    <LeadCardPreview lead={item.lead_card} />
                    <p className="mt-3 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                      View conversation →
                    </p>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
