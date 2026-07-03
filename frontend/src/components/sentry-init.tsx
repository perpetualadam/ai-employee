"use client";

import { useEffect } from "react";

import * as Sentry from "@sentry/nextjs";

let initialized = false;

/** Initializes browser Sentry when NEXT_PUBLIC_SENTRY_DSN is set. */
export function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn || initialized) return;
    Sentry.init({
      dsn,
      environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
      tracesSampleRate: 0.1,
      sendDefaultPii: false,
    });
    initialized = true;
  }, []);
  return null;
}
