import { getToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d))).join(", ");
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  const authToken = token ?? getToken();
  if (authToken) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 204) {
    return undefined as T;
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(formatErrorDetail(body.detail), res.status);
  }

  return res.json() as Promise<T>;
}

export const api = {
  register: (data: { email: string; password: string; full_name: string }) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }, null),

  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }, null),

  getMe: () => request<User>("/auth/me"),
  getBusiness: () => request<Business>("/business"),
  updateBusiness: (data: Partial<Business>) =>
    request<Business>("/business", { method: "PATCH", body: JSON.stringify(data) }),
  getDashboard: () => request<DashboardSummary>("/dashboard"),

  // Customers
  listCustomers: (search?: string) =>
    request<Customer[]>(`/customers${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createCustomer: (data: CustomerInput) =>
    request<Customer>("/customers", { method: "POST", body: JSON.stringify(data) }),
  updateCustomer: (id: string, data: Partial<CustomerInput>) =>
    request<Customer>(`/customers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCustomer: (id: string) =>
    request<void>(`/customers/${id}`, { method: "DELETE" }),

  // Jobs
  listJobs: (params?: { status?: string; customer_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.customer_id) qs.set("customer_id", params.customer_id);
    const query = qs.toString();
    return request<Job[]>(`/jobs${query ? `?${query}` : ""}`);
  },
  createJob: (data: JobInput) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify(data) }),
  updateJob: (id: string, data: Partial<JobInput>) =>
    request<Job>(`/jobs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteJob: (id: string) =>
    request<void>(`/jobs/${id}`, { method: "DELETE" }),

  // Appointments
  listAppointments: (params?: { start?: string; end?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.start) qs.set("start", params.start);
    if (params?.end) qs.set("end", params.end);
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString();
    return request<Appointment[]>(`/appointments${query ? `?${query}` : ""}`);
  },
  getAvailability: (date: string, durationMinutes = 60, excludeAppointmentId?: string) => {
    const qs = new URLSearchParams({ date, duration_minutes: String(durationMinutes) });
    if (excludeAppointmentId) qs.set("exclude_appointment_id", excludeAppointmentId);
    return request<AvailabilityResponse>(`/appointments/availability?${qs}`);
  },
  bookAppointment: (data: AppointmentInput) =>
    request<Appointment>("/appointments", { method: "POST", body: JSON.stringify(data) }),
  updateAppointment: (id: string, data: Partial<AppointmentInput & { status?: string }>) =>
    request<Appointment>(`/appointments/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  cancelAppointment: (id: string) =>
    request<Appointment>(`/appointments/${id}/cancel`, { method: "POST" }),

  // AI Receptionist
  chatReceptionist: (data: {
    message: string;
    history: ChatMessage[];
    session_id?: string;
    caller_phone?: string;
  }) =>
    request<ChatResponse>("/receptionist/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Billing
  getBillingStatus: () => request<BillingStatus>("/billing/status"),
  createCheckout: (plan: "starter" | "pro") =>
    request<{ checkout_url: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
  createBillingPortal: () =>
    request<{ portal_url: string }>("/billing/portal", { method: "POST" }),

  // Onboarding
  getOnboardingStatus: () => request<OnboardingStatus>("/onboarding/status"),
  completeOnboarding: () => request<Business>("/onboarding/complete", { method: "POST" }),
  seedDefaults: () => request<{ services: number; emergency_rules: number }>("/onboarding/seed-defaults", { method: "POST" }),
  seedSampleData: () => request<{ customer_id: string; already_exists?: boolean }>("/onboarding/sample-data", { method: "POST" }),
};

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Business {
  id: string;
  owner_id: string;
  name: string;
  industry: string;
  country: string;
  timezone: string;
  currency: string;
  working_hours: Record<string, unknown>;
  ai_instructions: string | null;
  phone_number: string | null;
  escalation_phone: string | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerInput {
  name: string;
  phone: string;
  email?: string;
  address?: string;
  notes?: string;
}

export interface Customer {
  id: string;
  business_id: string;
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
}

export interface JobInput {
  customer_id: string;
  service_type: string;
  notes?: string;
  status?: string;
  appointment_time?: string;
  appointment_id?: string;
}

export interface Job {
  id: string;
  business_id: string;
  customer_id: string;
  appointment_id: string | null;
  service_type: string;
  notes: string | null;
  status: string;
  appointment_time: string | null;
  created_at: string;
}

export interface AppointmentInput {
  customer_id: string;
  service_type: string;
  start_time: string;
  end_time: string;
  notes?: string;
}

export interface Appointment {
  id: string;
  business_id: string;
  customer_id: string;
  service_type: string;
  start_time: string;
  end_time: string;
  status: string;
  notes: string | null;
  confirmation_sent_at: string | null;
  created_at: string;
}

export interface AvailabilitySlot {
  start_time: string;
  end_time: string;
}

export interface AvailabilityResponse {
  date: string;
  duration_minutes: number;
  slots: AvailabilitySlot[];
}

export interface CallLog {
  id: string;
  business_id: string;
  customer_id: string | null;
  direction: string;
  status: string;
  caller_phone: string | null;
  duration_seconds: number | null;
  summary: string | null;
  escalated: boolean;
  created_at: string;
}

export interface AIActivity {
  id: string;
  business_id: string;
  call_log_id: string | null;
  action: string;
  tool_name: string | null;
  created_at: string;
}

export interface DashboardSummary {
  today_appointments: Appointment[];
  recent_calls: CallLog[];
  recent_customers: Customer[];
  recent_jobs: Job[];
  recent_ai_activity: AIActivity[];
  stats: {
    customers_total: number;
    jobs_open: number;
    appointments_today: number;
    calls_this_week: number;
  };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  tools_used: string[];
  escalated: boolean;
}

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  href: string;
}

export interface OnboardingStatus {
  onboarding_completed: boolean;
  steps: OnboardingStep[];
  completed_count: number;
  total_steps: number;
  progress_percent: number;
}

export interface BillingStatus {
  subscription_status: string;
  plan_tier: string;
  plan_label: string;
  plan_description: string;
  is_active: boolean;
  trial_ends_at: string | null;
  subscription_period_end: string | null;
  has_stripe_customer: boolean;
  usage: {
    calls_this_month: number;
    calls_limit: number;
    calls_remaining: number;
    ai_tool_calls_this_month: number;
    ai_tool_calls_limit: number;
  };
  limits: {
    calls_per_month: number;
    ai_messages_per_month: number;
  };
}

export function formatTime(iso: string, timezone?: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export function formatDate(iso: string, timezone?: string) {
  return new Date(iso).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: timezone,
  });
}

export function formatDateTime(iso: string, timezone?: string) {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export const JOB_STATUSES = [
  "lead",
  "quoted",
  "scheduled",
  "in_progress",
  "completed",
  "cancelled",
] as const;

export const APPOINTMENT_STATUSES = [
  "scheduled",
  "confirmed",
  "cancelled",
  "completed",
  "no_show",
] as const;
