"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import {
  CustomerChatSkeleton,
  CustomerErrorState,
} from "@/components/customer/customer-shell";
import { CustomerChat } from "@/components/customer-chat";
import { api, ApiError } from "@/lib/api";

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
    return <CustomerChatSkeleton />;
  }

  if (error) {
    return (
      <CustomerErrorState
        title="Chat unavailable"
        message={error}
        actionLabel="Learn about AI Employee"
        actionHref="/"
      />
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
