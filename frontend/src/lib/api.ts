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
  getProviderSettings: () => request<ProviderSettings>("/business/provider-settings"),
  updateBusiness: (data: Partial<Business> & { provider_config?: Record<string, string> }) =>
    request<Business>("/business", { method: "PATCH", body: JSON.stringify(data) }),
  getPhoneProvisioningStatus: () =>
    request<PhoneProvisioningStatus>("/business/phone/status"),
  searchAvailablePhoneNumbers: (prefix?: string, numberType?: string) => {
    const qs = new URLSearchParams();
    if (prefix) qs.set("prefix", prefix);
    if (numberType) qs.set("number_type", numberType);
    const query = qs.toString();
    return request<PhoneSearchResult>(
      `/business/phone/available${query ? `?${query}` : ""}`,
    );
  },
  provisionPhoneNumber: (phone_number: string) =>
    request<PhoneProvisionResult>("/business/phone/provision", {
      method: "POST",
      body: JSON.stringify({ phone_number }),
    }),
  getVerificationRequirements: () =>
    request<VerificationRequirements>("/business/phone/verification/requirements"),
  getVerificationStatus: () =>
    request<VerificationStatus>("/business/phone/verification/status"),
  uploadVerificationDocument: async (documentType: string, file: File) => {
    const form = new FormData();
    form.append("document_type", documentType);
    form.append("file", file);
    const token = getToken();
    const headers: HeadersInit = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${API_URL}/business/phone/verification/documents`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(formatErrorDetail(body.detail), res.status);
    }
    return res.json() as Promise<VerificationDocument>;
  },
  submitVerification: (data: VerificationSubmitInput) =>
    request<VerificationStatus>("/business/phone/verification/submit", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  placeOutboundCall: (data: { customer_id?: string; phone?: string; reason?: string }) =>
    request<OutboundCallResult>("/calls/outbound", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getDashboard: () => request<DashboardSummary>("/dashboard"),
  listConversations: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return request<ConversationListItem[]>(`/conversations${query ? `?${query}` : ""}`);
  },
  getConversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),

  getAddressConfirmInfo: (token: string) =>
    request<AddressConfirmInfo>(`/public/address-confirm/${token}`, {}, null),
  submitAddressConfirm: (token: string, address: string) =>
    request<AddressConfirmResult>(`/public/address-confirm/${token}`, {
      method: "POST",
      body: JSON.stringify({ address }),
    }, null),

  getPublicChatInfo: (slug: string) =>
    request<PublicChatInfo>(`/public/chat/${slug}`, {}, null),

  publicChat: (
    slug: string,
    data: {
      message: string;
      history: ChatMessage[];
      session_id?: string;
      customer_phone?: string;
    },
  ) =>
    request<PublicChatResponse>(`/public/chat/${slug}`, {
      method: "POST",
      body: JSON.stringify(data),
    }, null),

  getPublicContinueInfo: (token: string) =>
    request<PublicContinueInfo>(`/public/continue/${token}`, {}, null),

  publicChatContinue: (
    token: string,
    data: {
      message: string;
      history: ChatMessage[];
      session_id?: string;
      customer_phone?: string;
    },
  ) =>
    request<PublicChatResponse>(`/public/continue/${token}`, {
      method: "POST",
      body: JSON.stringify(data),
    }, null),

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
  bulkCancelAppointments: (appointmentIds: string[]) =>
    request<{ cancelled: number; skipped: number }>("/appointments/bulk-cancel", {
      method: "POST",
      body: JSON.stringify({ appointment_ids: appointmentIds }),
    }),

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
  getTrades: () => request<TradeOption[]>("/onboarding/trades"),
  getCountries: () => request<CountryOption[]>("/onboarding/countries"),
  completeOnboarding: () => request<Business>("/onboarding/complete", { method: "POST" }),
  seedDefaults: () =>
    request<{ services: number; emergency_rules: number; industry: string }>(
      "/onboarding/seed-defaults",
      { method: "POST" },
    ),
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
  phone_provisioned?: boolean;
  reminders_enabled?: boolean;
  escalation_phone: string | null;
  provider_config?: Record<string, string>;
  public_slug: string | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderSettings {
  provider_config: Record<string, string>;
  country_defaults: Record<string, string>;
  global_defaults: Record<string, string>;
  available: Record<string, string[]>;
}

export interface TradeOption {
  value: string;
  label: string;
  services: string[];
  emergency_rules: string[];
}

export interface CountryOption {
  code: string;
  label: string;
  timezone?: string;
  currency?: string;
}

export interface PhoneProvisioningStatus {
  phone_number: string | null;
  provisioned: boolean;
  platform_configured: boolean;
  can_search: boolean;
  manual_fallback_allowed: boolean;
  country: string;
  prefix_label?: string;
  prefix_example?: string;
  prefix_supported?: boolean;
  example_phone?: string;
  default_number_type?: string | null;
  number_type_options?: { value: string; label: string }[];
  verification_required?: boolean;
  verification_status?: string | null;
  verification_approved?: boolean;
}

export interface VerificationRequirements {
  country_code: string;
  country_name?: string;
  verification_required: boolean;
  requires_end_user?: boolean;
  requires_regulatory_bundle?: boolean;
  required_documents: string[];
  metadata?: Record<string, unknown>;
}

export interface VerificationDocument {
  id: string;
  document_type: string;
  verification_status: string;
  storage_key: string;
  provider_document_id?: string | null;
  created_at: string;
}

export interface VerificationStatus {
  country_code: string;
  status: string;
  provider_end_user_id?: string | null;
  provider_bundle_id?: string | null;
  last_checked?: string | null;
  uploaded_documents: VerificationDocument[];
}

export interface VerificationSubmitInput {
  business_name: string;
  contact_email?: string;
  address?: string;
}

export interface AvailablePhoneNumber {
  phone_number: string;
  region?: string | null;
  cost?: string | null;
}

export interface PhoneSearchResult {
  numbers: AvailablePhoneNumber[];
  country: string;
  prefix_label: string;   // e.g. "Area code" (US), "City / area" (GB), "STD area code" (AU)
  prefix_example: string; // placeholder for the UI input
  prefix_supported?: boolean;
  number_type?: string | null;
  number_type_options?: { value: string; label: string }[];
}

export interface PhoneProvisionResult {
  phone_number: string;
  provisioned: boolean;
  telnyx_phone_number_id?: string | null;
  message: string;
}

export interface OutboundCallResult {
  call_log_id: string;
  status: string;
  external_call_id?: string | null;
  message: string;
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
  ai_summary?: string | null;
  escalated: boolean;
  created_at: string;
}

export interface ConversationLeadCard {
  customer_name: string | null;
  customer_phone: string | null;
  service_address: string | null;
  service_type: string | null;
  appointment_time: string | null;
  is_booked: boolean;
  is_escalated: boolean;
  is_emergency: boolean;
}

export interface ConversationListItem {
  id: string;
  channel: string;
  channel_label: string;
  status: string;
  caller_phone: string | null;
  summary: string | null;
  ai_summary: string | null;
  escalated: boolean;
  is_booked: boolean;
  created_at: string;
  lead_card: ConversationLeadCard;
}

export interface ConversationMessage {
  role: "user" | "assistant" | "system";
  content: string;
  channel?: string | null;
}

export interface ConversationActivity {
  id: string;
  action: string;
  tool_name: string | null;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  business_id: string;
  customer_id: string | null;
  channel: string;
  channel_label: string;
  status: string;
  caller_phone: string | null;
  duration_seconds: number | null;
  summary: string | null;
  ai_summary: string | null;
  escalated: boolean;
  created_at: string;
  transcript: string | null;
  messages: ConversationMessage[];
  activities: ConversationActivity[];
  lead_card: ConversationLeadCard;
}

export interface AddressConfirmInfo {
  business_name: string;
  customer_name: string | null;
  already_confirmed: boolean;
  confirmed_address: string | null;
}

export interface AddressConfirmResult {
  success: boolean;
  address: string | null;
  message: string;
}

export interface PublicChatInfo {
  business_name: string;
  public_slug: string;
  phone_number: string | null;
}

export interface PublicContinueInfo {
  business_name: string;
  session_id: string;
  phone_number: string | null;
  messages: ChatMessage[];
  voice_handoff: boolean;
}

export interface PublicChatResponse {
  reply: string;
  session_id: string;
  tools_used: string[];
  escalated: boolean;
  owner_notified: boolean;
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
  owner_notified: boolean;
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
