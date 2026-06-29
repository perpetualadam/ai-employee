import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/40">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            AI
          </div>
          <span className="font-semibold">AI Employee</span>
        </div>
        <div className="flex gap-3">
          <Link href="/login" className={cn(buttonVariants({ variant: "ghost" }))}>
            Sign in
          </Link>
          <Link href="/register" className={cn(buttonVariants())}>
            Get started
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-20 text-center">
        <p className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Built for trade businesses
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          Your 24/7 AI receptionist that answers calls, books jobs, and updates your CRM
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Not a chatbot. An AI employee that qualifies leads, schedules appointments,
          sends confirmations, and escalates emergencies — so you can focus on the work.
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

        <div className="mt-20 grid gap-6 text-left sm:grid-cols-3">
          {[
            {
              title: "Answers every call",
              body: "Introduces itself, collects customer details, and understands why they're calling.",
            },
            {
              title: "Books appointments",
              body: "Checks availability, schedules jobs, and sends SMS and email confirmations.",
            },
            {
              title: "Knows when to escalate",
              body: "Detects emergencies and transfers to a human when your rules say so.",
            },
          ].map((feature) => (
            <div key={feature.title} className="rounded-xl border bg-card p-6">
              <h3 className="font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{feature.body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
