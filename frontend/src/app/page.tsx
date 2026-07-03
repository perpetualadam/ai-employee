import Link from "next/link";
import {
  Calendar,
  MessageSquare,
  Phone,
  Shield,
  Sparkles,
  Wrench,
} from "lucide-react";

import { SentryInit } from "@/components/sentry-init";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const TRADES = [
  "Plumbing",
  "Gas & heating",
  "Mobile mechanic",
  "Electrician",
  "HVAC",
  "Roofing",
  "Landscaping",
  "Cleaning",
];

const STEPS = [
  {
    icon: Phone,
    title: "Answers every call",
    body: "Trade-specific greeting, intake, and emergency detection — 24/7 on your business number.",
  },
  {
    icon: Calendar,
    title: "Books real jobs",
    body: "Checks your calendar, offers open slots, confirms by SMS and email, and updates your CRM.",
  },
  {
    icon: MessageSquare,
    title: "Escalates when it matters",
    body: "Transfers urgent calls or notifies you by SMS and email when a human needs to step in.",
  },
];

const PROOF = [
  "14 trade templates with country-aware compliance",
  "Voice + text receptionist on one platform",
  "Stripe billing with free trial",
  "Self-serve phone provisioning via Telnyx",
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-muted/50">
      <SentryInit />

      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
              AI
            </div>
            <span className="font-semibold">AI Employee</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            <Link href="/login" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
              Sign in
            </Link>
            <Link href="/register" className={cn(buttonVariants({ size: "sm" }))}>
              Start free trial
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-6xl px-6 pb-16 pt-16 text-center sm:pt-24">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-muted/60 px-4 py-1.5 text-sm">
            <Sparkles className="size-4 text-primary" />
            <span className="font-medium">Fair launch — now onboarding trade businesses</span>
          </div>

          <h1 className="mx-auto max-w-4xl text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            Your AI receptionist that never misses a lead
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground sm:text-xl">
            Answers calls, qualifies customers, books appointments, and keeps your CRM
            up to date — built for plumbers, gas engineers, mechanics, and every trade
            in between.
          </p>

          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link href="/register" className={cn(buttonVariants({ size: "lg" }))}>
              Start free trial
            </Link>
            <Link
              href="/login"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              Sign in to dashboard
            </Link>
          </div>

          <p className="mt-4 text-sm text-muted-foreground">
            No credit card required to explore · Set up in minutes
          </p>
        </section>

        <section className="border-y bg-muted/30 py-10">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-8 gap-y-3 px-6 text-sm text-muted-foreground">
            {PROOF.map((item) => (
              <span key={item} className="flex items-center gap-2">
                <Shield className="size-4 shrink-0 text-primary" />
                {item}
              </span>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20">
          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Built for your trade</h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Pick your industry at signup — services, prompts, and compliance hints are
              pre-configured. Customize anything in onboarding.
            </p>
          </div>
          <div className="mt-10 flex flex-wrap justify-center gap-2">
            {TRADES.map((trade) => (
              <span
                key={trade}
                className="inline-flex items-center gap-1.5 rounded-full border bg-card px-4 py-2 text-sm font-medium"
              >
                <Wrench className="size-3.5 text-muted-foreground" />
                {trade}
              </span>
            ))}
            <span className="inline-flex items-center rounded-full border border-dashed px-4 py-2 text-sm text-muted-foreground">
              + 6 more trades
            </span>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-20">
          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">How it works</h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              One AI employee handles the front desk while you&apos;re on the job.
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.title} className="rounded-xl border bg-card p-6 text-left shadow-sm">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <step.icon className="size-5" />
                </div>
                <h3 className="font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t bg-primary px-6 py-16 text-primary-foreground">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Stop losing jobs to voicemail
            </h2>
            <p className="mt-4 text-primary-foreground/85">
              Join the fair launch — get your AI receptionist live, provision a local
              number, and start booking while you&apos;re still on the tools.
            </p>
            <Link
              href="/register"
              className={cn(
                buttonVariants({ size: "lg", variant: "secondary" }),
                "mt-8",
              )}
            >
              Create your account
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} AI Employee · AI receptionist for trade businesses</p>
      </footer>
    </div>
  );
}
