"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { CustomerChat } from "@/components/customer-chat";
import { api, ApiError, ChatMessage } from "@/lib/api";

export default function PublicChatPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [businessName, setBusinessName] = useState("");

  useEffect(() => {
    api
      .getPublicChatInfo(slug)
      .then((info) => {
        setBusinessName(info.business_name);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Business not found");
      })
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4 text-center text-muted-foreground">
        {error}
      </div>
    );
  }

  return (
    <CustomerChat
      businessName={businessName}
      onSend={async ({ message, history, sessionId, customerPhone }) =>
        api.publicChat(slug, {
          message,
          history,
          session_id: sessionId ?? undefined,
          customer_phone: customerPhone,
        })
      }
    />
  );
}
