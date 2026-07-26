"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, Business } from "@/lib/api";

export function useDashboardAuth() {
  const router = useRouter();
  const [businessName, setBusinessName] = useState("Your Business");
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshBusiness = useCallback(async () => {
    const biz = await api.getBusiness();
    setBusiness(biz);
    setBusinessName(biz.name);
    return biz;
  }, []);

  useEffect(() => {
    api
      .getBusiness()
      .then((biz) => {
        setBusiness(biz);
        setBusinessName(biz.name);
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  return { business, businessName, loading, refreshBusiness };
}
