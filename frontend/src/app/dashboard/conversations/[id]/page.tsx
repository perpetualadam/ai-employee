"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { DashboardShell } from "@/components/dashboard/shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import { api, ConversationDetail, formatDateTime } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function ConversationDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .getConversation(id)
      .then(setDetail)
      .catch(() => router.replace("/dashboard/conversations"))
      .finally(() => setLoading(false));
  }, [authLoading, id, router]);

  const tz = business?.timezone;

  if (authLoading || loading || !detail) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading conversation...</p>
      </div>
    );
  }

  const lead = detail.lead_card;

  return (
    <DashboardShell businessName={businessName}>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link href="/dashboard/conversations">Back to inbox</Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {lead.customer_name || detail.caller_phone || "Conversation"}
            </h1>
            <p className="text-sm text-muted-foreground">
              {detail.channel_label} · {formatDateTime(detail.created_at, tz)}
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Lead summary</CardTitle>
            <CardDescription>What the AI captured for your team</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            <p><span className="font-medium">Phone:</span> {lead.customer_phone || "—"}</p>
            <p><span className="font-medium">Service:</span> {lead.service_type || "—"}</p>
            <p className="sm:col-span-2"><span className="font-medium">Address:</span> {lead.service_address || "—"}</p>
            <p><span className="font-medium">Appointment:</span> {lead.appointment_time ? formatDateTime(lead.appointment_time, tz) : "—"}</p>
            <div className="flex flex-wrap gap-2">
              {lead.is_booked && <Badge>Booked</Badge>}
              {lead.is_emergency && <Badge variant="destructive">Urgent</Badge>}
              {detail.escalated && <Badge variant="destructive">Escalated</Badge>}
            </div>
            {detail.ai_summary && (
              <p className="sm:col-span-2 rounded-md bg-muted p-3">{detail.ai_summary}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {detail.messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">No messages recorded.</p>
            ) : (
              detail.messages.map((msg, i) => (
                <div
                  key={`${msg.role}-${i}`}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "ml-8 bg-primary/10"
                      : msg.role === "assistant"
                        ? "mr-8 bg-muted"
                        : "bg-muted/50 italic text-muted-foreground"
                  }`}
                >
                  <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                    {msg.role}
                    {msg.channel ? ` · ${msg.channel}` : ""}
                  </p>
                  <p>{msg.content}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {detail.activities.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Behind the scenes</CardTitle>
              <CardDescription>Tool calls during this conversation</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {detail.activities.map((act) => (
                <div key={act.id} className="rounded border px-3 py-2">
                  <p className="font-medium">{act.tool_name || act.action}</p>
                  <p className="text-xs text-muted-foreground">{formatDateTime(act.created_at, tz)}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardShell>
  );
}
