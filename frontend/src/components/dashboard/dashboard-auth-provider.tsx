"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { api, Business } from "@/lib/api";

interface DashboardAuthContextValue {
  business: Business | null;
  businessName: string;
  loading: boolean;
  refreshBusiness: () => Promise<Business>;
}

const DashboardAuthContext = createContext<DashboardAuthContextValue | null>(
  null,
);

export function DashboardAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
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

  const value = useMemo(
    () => ({ business, businessName, loading, refreshBusiness }),
    [business, businessName, loading, refreshBusiness],
  );

  return (
    <DashboardAuthContext.Provider value={value}>
      {children}
    </DashboardAuthContext.Provider>
  );
}

export function useDashboardAuth() {
  const context = useContext(DashboardAuthContext);
  if (!context) {
    throw new Error("useDashboardAuth must be used within DashboardAuthProvider");
  }
  return context;
}
