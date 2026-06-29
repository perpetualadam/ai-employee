"use client";

import { useRef, useState } from "react";

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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import { api, ApiError, ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ReceptionistPage() {
  const { businessName, loading: authLoading } = useDashboardAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [callerPhone, setCallerPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [lastTools, setLastTools] = useState<string[]>([]);
  const [escalated, setEscalated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setError("");
    setSending(true);

    const userMessage: ChatMessage = { role: "user", content: text };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);

    try {
      const response = await api.chatReceptionist({
        message: text,
        history: messages,
        session_id: sessionId ?? undefined,
        caller_phone: callerPhone || undefined,
      });

      setSessionId(response.session_id);
      setLastTools(response.tools_used);
      setEscalated(response.escalated);
      setMessages([...nextMessages, { role: "assistant", content: response.reply }]);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reach AI receptionist");
      setMessages(messages);
    } finally {
      setSending(false);
    }
  }

  function handleNewSession() {
    setMessages([]);
    setSessionId(null);
    setLastTools([]);
    setEscalated(false);
    setError("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <DashboardShell businessName={businessName}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Receptionist</h1>
            <p className="text-muted-foreground">
              Test your receptionist — simulates a customer conversation
            </p>
          </div>
          <Button variant="outline" onClick={handleNewSession}>
            New conversation
          </Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Conversation</CardTitle>
              <CardDescription>
                {sessionId ? `Session: ${sessionId.slice(0, 8)}...` : "Start a new session"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="h-[420px] overflow-y-auto rounded-lg border bg-background p-4">
                {messages.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                    <p>
                      Try: &quot;Hi, I have a leak under my kitchen sink and need someone to come
                      look at it.&quot;
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        className={cn(
                          "flex",
                          msg.role === "user" ? "justify-end" : "justify-start",
                        )}
                      >
                        <div
                          className={cn(
                            "max-w-[85%] rounded-lg px-3 py-2 text-sm",
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
                          Thinking...
                        </div>
                      </div>
                    )}
                    <div ref={bottomRef} />
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type as a customer..."
                  rows={2}
                  disabled={sending || escalated}
                />
                <Button onClick={handleSend} disabled={sending || !input.trim() || escalated}>
                  Send
                </Button>
              </div>

              {escalated && (
                <p className="text-sm text-amber-600">
                  Conversation escalated to a human. Start a new session to continue testing.
                </p>
              )}
              {error && <p className="text-sm text-destructive">{error}</p>}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Simulate caller</CardTitle>
                <CardDescription>Optional test phone number</CardDescription>
              </CardHeader>
              <CardContent>
                <Input
                  value={callerPhone}
                  onChange={(e) => setCallerPhone(e.target.value)}
                  placeholder="+1 555 0100"
                  disabled={!!sessionId}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>AI activity</CardTitle>
                <CardDescription>Tools used in last response</CardDescription>
              </CardHeader>
              <CardContent>
                {lastTools.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No tools used yet.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {lastTools.map((tool) => (
                      <Badge key={tool} variant="secondary">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tips</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>The AI will ask for name, phone, address, and reason for calling.</p>
                <p>It uses real CRM and calendar tools — bookings appear in your dashboard.</p>
                <p>Requires GROQ_API_KEY on the backend.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
