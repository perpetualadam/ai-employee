"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface CustomerChatProps {
  businessName: string;
  subtitle?: string;
  initialMessages?: ChatMessage[];
  sessionId?: string | null;
  showPhoneField?: boolean;
  voiceHandoff?: boolean;
  onSend: (payload: {
    message: string;
    history: ChatMessage[];
    sessionId?: string | null;
    customerPhone?: string;
  }) => Promise<{
    reply: string;
    session_id: string;
    escalated: boolean;
  }>;
}

export function CustomerChat({
  businessName,
  subtitle,
  initialMessages = [],
  sessionId: initialSessionId = null,
  showPhoneField = true,
  voiceHandoff = false,
  onSend,
}: CustomerChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId);
  const [customerPhone, setCustomerPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [escalated, setEscalated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending || escalated) return;

    setInput("");
    setError("");
    setSending(true);

    const userMessage: ChatMessage = { role: "user", content: text };
    const prior = messages;
    const nextMessages = [...prior, userMessage];
    setMessages(nextMessages);

    try {
      const response = await onSend({
        message: text,
        history: prior,
        sessionId,
        customerPhone: customerPhone || undefined,
      });
      setSessionId(response.session_id);
      setEscalated(response.escalated);
      setMessages([...nextMessages, { role: "assistant", content: response.reply }]);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setMessages(prior);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col bg-muted/30 p-4">
      <Card className="flex flex-1 flex-col shadow-md">
        <CardHeader className="border-b pb-4">
          <CardTitle className="text-lg">{businessName}</CardTitle>
          <CardDescription>
            {subtitle ??
              (voiceHandoff
                ? "Continue your conversation — type your details below"
                : "Chat with our AI receptionist — book service or ask a question")}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 pt-4">
          {showPhoneField && !sessionId && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Your phone number (optional)
              </label>
              <Input
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+1 555 0100"
              />
            </div>
          )}

          <div className="min-h-[360px] flex-1 overflow-y-auto rounded-lg border bg-background p-4">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                <p>
                  Example: &quot;Hi, I have a leak under my kitchen sink and need someone to come
                  look at it.&quot;
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
                  >
                    <div
                      className={cn(
                        "max-w-[90%] rounded-lg px-3 py-2 text-sm",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted",
                      )}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                      Typing…
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          {escalated ? (
            <p className="text-sm text-muted-foreground">
              A team member will follow up with you shortly. You can close this page.
            </p>
          ) : (
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message…"
                rows={2}
                disabled={sending}
              />
              <Button onClick={handleSend} disabled={sending || !input.trim()}>
                Send
              </Button>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
