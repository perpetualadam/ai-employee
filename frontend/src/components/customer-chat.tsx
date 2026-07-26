"use client";

import { Loader2, MessageSquare, Phone, Send } from "lucide-react";
import { useRef, useState } from "react";

import { CustomerShell } from "@/components/customer/customer-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const examplePrompts = [
  "I have a leak under my kitchen sink",
  "Can I book a service call this week?",
  "What are your hours?",
];

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

function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-live="polite" aria-label="Assistant is typing">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-border/80 bg-muted/80 px-4 py-3">
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.2s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.1s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
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

  const defaultSubtitle = voiceHandoff
    ? "Continue your conversation — share details and book online"
    : "Chat with our AI receptionist — book service or ask a question";

  async function handleSend(textOverride?: string) {
    const text = (textOverride ?? input).trim();
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
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
      );
      setMessages(prior);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <CustomerShell
      businessName={businessName}
      description={subtitle ?? defaultSubtitle}
      badge={voiceHandoff ? "Voice handoff" : "Online chat"}
      compact
      className="pb-2"
    >
      {voiceHandoff && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm">
          <Phone className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
          <p className="text-muted-foreground">
            You started on a call — finish booking here by typing your name, address, and
            preferred time.
          </p>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
        <div
          className="min-h-[min(420px,55dvh)] flex-1 overflow-y-auto p-4 sm:p-5"
          role="log"
          aria-live="polite"
          aria-relevant="additions"
          aria-label="Chat messages"
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-6 py-8 text-center">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <MessageSquare className="size-7" aria-hidden />
              </div>
              <div className="space-y-2">
                <p className="font-medium">How can we help you today?</p>
                <p className="max-w-xs text-sm text-muted-foreground">
                  Ask about service, availability, or describe what you need — our AI
                  receptionist is here 24/7.
                </p>
              </div>
              {!escalated && (
                <div className="flex flex-wrap justify-center gap-2">
                  {examplePrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void handleSend(prompt)}
                      disabled={sending}
                      className="rounded-full border border-border/80 bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <div
                  key={`${msg.role}-${index}`}
                  className={cn(
                    "flex",
                    msg.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[88%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                      msg.role === "user"
                        ? "rounded-2xl rounded-br-md bg-primary text-primary-foreground shadow-sm"
                        : "rounded-2xl rounded-bl-md border border-border/60 bg-muted/50",
                    )}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {sending && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="border-t border-border/60 bg-muted/20 p-3 sm:p-4">
          {escalated ? (
            <p className="rounded-lg border border-success/30 bg-success/5 px-4 py-3 text-sm text-muted-foreground">
              A team member will follow up with you shortly. You can close this page.
            </p>
          ) : (
            <div className="space-y-3">
              {showPhoneField && !sessionId && (
                <div className="space-y-1.5">
                  <label
                    htmlFor="customer-phone"
                    className="text-xs font-medium text-muted-foreground"
                  >
                    Your phone number (optional)
                  </label>
                  <Input
                    id="customer-phone"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    placeholder="+1 555 010 1234"
                    autoComplete="tel"
                  />
                </div>
              )}

              <div className="flex items-end gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your message…"
                  rows={2}
                  disabled={sending}
                  className="min-h-[44px] resize-none bg-background"
                  aria-label="Message"
                />
                <Button
                  onClick={() => void handleSend()}
                  disabled={sending || !input.trim()}
                  size="icon-lg"
                  className="shrink-0"
                  aria-label="Send message"
                >
                  {sending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Send className="size-4" />
                  )}
                </Button>
              </div>
            </div>
          )}

          {error && (
            <p
              className="mt-3 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              role="alert"
            >
              {error}
            </p>
          )}
        </div>
      </div>
    </CustomerShell>
  );
}
