"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { CustomerChat } from "@/components/customer-chat";
import { api, ApiError, ChatMessage } from "@/lib/api";

export default function ContinueChatPage() {
  const params = useParams();
  const token = params.token as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [initialMessages, setInitialMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    api
      .getPublicContinueInfo(token)
      .then((info) => {
        setBusinessName(info.business_name);
        setSessionId(info.session_id);
        setInitialMessages(info.messages as ChatMessage[]);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "This link is invalid or has expired.");
      })
      .finally(() => setLoading(false));
  }, [token]);

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
      voiceHandoff
      initialMessages={initialMessages}
      sessionId={sessionId}
      showPhoneField={false}
      onSend={async ({ message, history, sessionId, customerPhone }) =>
        api.publicChatContinue(token, {
          message,
          history,
          session_id: sessionId ?? undefined,
          customer_phone: customerPhone,
        })
      }
    />
  );
}
