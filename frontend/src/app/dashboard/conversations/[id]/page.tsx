"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { PageHeader } from "@/components/dashboard/page-header";
import { InboxSkeleton } from "@/components/dashboard/page-skeletons";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import { api, ApiError, ConversationDetail, formatDateTime } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ConversationDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const { business, loading: authLoading } = useDashboardAuth();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [calling, setCalling] = useState(false);
  const [callMessage, setCallMessage] = useState("");

  useEffect(() => {
    if (authLoading) return;
    api
      .getConversation(id)
      .then(setDetail)
      .catch(() => router.replace("/dashboard/conversations"))
      .finally(() => setLoading(false));
  }, [authLoading, id, router]);

  const tz = business?.timezone;

  if (authLoading || loading || !detail) {
    return <InboxSkeleton />;
  }

  const conversation = detail;
  const lead = conversation.lead_card;

  async function handleCallBack() {
    setCalling(true);
    setCallMessage("");
    try {
      const result = await api.placeOutboundCall({
        customer_id: conversation.customer_id ?? undefined,
        phone: lead.customer_phone ?? conversation.caller_phone ?? undefined,
        reason: conversation.ai_summary || conversation.summary || undefined,
      });
      setCallMessage(result.message);
    } catch (err) {
      setCallMessage(err instanceof ApiError ? err.message : "Could not place call");
    } finally {
      setCalling(false);
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <PageHeader
        title={lead.customer_name || detail.caller_phone || "Conversation"}
        description={`${detail.channel_label} · ${formatDateTime(detail.created_at, tz)}`}
        actions={
          <Link
            href="/dashboard/conversations"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Back to inbox
          </Link>
        }
      />

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
            {(lead.customer_phone || detail.caller_phone) && (
              <div className="sm:col-span-2 flex flex-wrap items-center gap-3 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={calling}
                  onClick={handleCallBack}
                >
                  {calling ? "Calling…" : "Call customer back"}
                </Button>
                {callMessage && (
                  <p className="text-sm text-muted-foreground">{callMessage}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {detail.messages.length === 0 && !detail.transcript ? (
              <p className="text-sm text-muted-foreground">No messages recorded.</p>
            ) : detail.messages.length === 0 && detail.transcript ? (
              <pre className="whitespace-pre-wrap rounded-lg bg-muted p-3 text-sm font-sans">
                {detail.transcript}
              </pre>
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
  );
}
