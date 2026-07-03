"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import {
  api,
  ApiError,
  Appointment,
  AvailabilitySlot,
  Customer,
  formatDateTime,
  formatTime,
} from "@/lib/api";

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function CalendarPage() {
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [selectedDate, setSelectedDate] = useState(todayIsoDate());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [rescheduleSlots, setRescheduleSlots] = useState<AvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [bookOpen, setBookOpen] = useState(false);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] = useState<Appointment | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [customerId, setCustomerId] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkCancelling, setBulkCancelling] = useState(false);

  const tz = business?.timezone;
  const customerMap = useMemo(
    () => Object.fromEntries(customers.map((c) => [c.id, c.name])),
    [customers],
  );

  const loadDay = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const start = new Date(`${date}T00:00:00`).toISOString();
      const end = new Date(`${date}T23:59:59`).toISOString();
      const [appts, avail, custs] = await Promise.all([
        api.listAppointments({ start, end }),
        api.getAvailability(date),
        api.listCustomers(),
      ]);
      setAppointments(appts.filter((a) => a.status !== "cancelled"));
      setSlots(avail.slots);
      setCustomers(custs);
      setSelectedIds(new Set());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading) loadDay(selectedDate);
  }, [authLoading, selectedDate, loadDay]);

  function openBook(slot: AvailabilitySlot) {
    setSelectedSlot(slot);
    setCustomerId("");
    setServiceType("");
    setNotes("");
    setError("");
    setBookOpen(true);
  }

  async function openReschedule(appt: Appointment) {
    setRescheduleTarget(appt);
    setSelectedSlot(null);
    setError("");
    setRescheduleOpen(true);
    try {
      const avail = await api.getAvailability(selectedDate, 60, appt.id);
      setRescheduleSlots(avail.slots);
    } catch {
      setRescheduleSlots([]);
    }
  }

  async function handleBook() {
    if (!selectedSlot) return;
    setSaving(true);
    setError("");
    try {
      await api.bookAppointment({
        customer_id: customerId,
        service_type: serviceType,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        notes: notes || undefined,
      });
      setBookOpen(false);
      await loadDay(selectedDate);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to book appointment");
    } finally {
      setSaving(false);
    }
  }

  async function handleReschedule() {
    if (!rescheduleTarget || !selectedSlot) return;
    setSaving(true);
    setError("");
    try {
      await api.updateAppointment(rescheduleTarget.id, {
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
      });
      setRescheduleOpen(false);
      setRescheduleTarget(null);
      await loadDay(selectedDate);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reschedule");
    } finally {
      setSaving(false);
    }
  }

  async function handleCancel(appt: Appointment) {
    if (!confirm("Cancel this appointment?")) return;
    await api.cancelAppointment(appt.id);
    await loadDay(selectedDate);
  }

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === appointments.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(appointments.map((a) => a.id)));
    }
  }

  async function handleBulkCancel() {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    if (
      !confirm(
        `Cancel ${ids.length} selected appointment${ids.length === 1 ? "" : "s"}?`,
      )
    ) {
      return;
    }
    setBulkCancelling(true);
    try {
      await api.bulkCancelAppointments(ids);
      await loadDay(selectedDate);
    } finally {
      setBulkCancelling(false);
    }
  }

  const allSelected =
    appointments.length > 0 && selectedIds.size === appointments.length;
  const someSelected = selectedIds.size > 0 && !allSelected;

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
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Calendar</h1>
          <p className="text-muted-foreground">
            Book, reschedule, and cancel appointments
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-auto"
            />
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Available slots</CardTitle>
              <CardDescription>
                Based on your business working hours ({tz ?? "local time"})
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : slots.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No available slots for this date.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {slots.map((slot) => (
                    <Button
                      key={slot.start_time}
                      variant="outline"
                      size="sm"
                      onClick={() => openBook(slot)}
                    >
                      {formatTime(slot.start_time, tz)} – {formatTime(slot.end_time, tz)}
                    </Button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Scheduled</CardTitle>
                  <CardDescription>Appointments on {selectedDate}</CardDescription>
                </div>
                {appointments.length > 0 && (
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="flex cursor-pointer items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={(el) => {
                          if (el) el.indeterminate = someSelected;
                        }}
                        onChange={toggleSelectAll}
                        className="size-4 rounded border-input"
                      />
                      Select all
                    </label>
                    {selectedIds.size > 0 && (
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={bulkCancelling}
                        onClick={handleBulkCancel}
                      >
                        {bulkCancelling
                          ? "Cancelling..."
                          : `Cancel selected (${selectedIds.size})`}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : appointments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No appointments scheduled.</p>
              ) : (
                <ul className="space-y-4">
                  {appointments.map((appt) => (
                    <li
                      key={appt.id}
                      className="flex flex-wrap items-start justify-between gap-3 rounded-lg border p-3"
                    >
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(appt.id)}
                          onChange={() => toggleSelected(appt.id)}
                          aria-label={`Select appointment at ${formatTime(appt.start_time, tz)}`}
                          className="mt-1 size-4 shrink-0 rounded border-input"
                        />
                        <div>
                          <p className="font-medium">
                            {formatTime(appt.start_time, tz)} – {formatTime(appt.end_time, tz)}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {customerMap[appt.customer_id] ?? "Unknown"} · {appt.service_type}
                          </p>
                          <Badge variant="secondary" className="mt-1">
                            {appt.status}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openReschedule(appt)}>
                          Reschedule
                        </Button>
                        <Button variant="destructive" size="sm" onClick={() => handleCancel(appt)}>
                          Cancel
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Book dialog */}
      <Dialog open={bookOpen} onOpenChange={setBookOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Book appointment</DialogTitle>
          </DialogHeader>
          {selectedSlot && (
            <p className="text-sm text-muted-foreground">
              {formatDateTime(selectedSlot.start_time, tz)} –{" "}
              {formatTime(selectedSlot.end_time, tz)}
            </p>
          )}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="book-customer">Customer</Label>
              <select
                id="book-customer"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-background px-2 text-sm"
              >
                <option value="">Select customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.phone})
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="book-service">Service</Label>
              <Input
                id="book-service"
                value={serviceType}
                onChange={(e) => setServiceType(e.target.value)}
                placeholder="e.g. Water heater repair"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="book-notes">Notes</Label>
              <Textarea
                id="book-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBookOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleBook}
              disabled={saving || !customerId || !serviceType}
            >
              {saving ? "Booking..." : "Book"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reschedule dialog */}
      <Dialog open={rescheduleOpen} onOpenChange={setRescheduleOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reschedule appointment</DialogTitle>
          </DialogHeader>
          {rescheduleTarget && (
            <p className="text-sm text-muted-foreground">
              Current: {formatDateTime(rescheduleTarget.start_time, tz)}
            </p>
          )}
          <div className="space-y-2">
            <Label>Pick a new slot</Label>
            {rescheduleSlots.length === 0 ? (
              <p className="text-sm text-muted-foreground">No slots available.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {rescheduleSlots.map((slot) => (
                  <Button
                    key={slot.start_time}
                    variant={selectedSlot?.start_time === slot.start_time ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedSlot(slot)}
                  >
                    {formatTime(slot.start_time, tz)}
                  </Button>
                ))}
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRescheduleOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleReschedule} disabled={saving || !selectedSlot}>
              {saving ? "Saving..." : "Reschedule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
}
