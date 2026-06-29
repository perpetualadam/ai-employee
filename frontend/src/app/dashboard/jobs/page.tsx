"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/dashboard/shell";
import { EmptyState } from "@/components/dashboard/empty-state";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useDashboardAuth } from "@/hooks/use-dashboard-auth";
import {
  api,
  ApiError,
  Customer,
  formatDateTime,
  JOB_STATUSES,
  Job,
  JobInput,
} from "@/lib/api";

const emptyForm: JobInput = {
  customer_id: "",
  service_type: "",
  notes: "",
  status: "lead",
};

export default function JobsPage() {
  const { businessName, business, loading: authLoading } = useDashboardAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Job | null>(null);
  const [form, setForm] = useState<JobInput>(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const customerMap = useMemo(
    () => Object.fromEntries(customers.map((c) => [c.id, c.name])),
    [customers],
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsData, customersData] = await Promise.all([
        api.listJobs(statusFilter ? { status: statusFilter } : undefined),
        api.listCustomers(),
      ]);
      setJobs(jobsData);
      setCustomers(customersData);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (!authLoading) loadData();
  }, [authLoading, loadData]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError("");
    setDialogOpen(true);
  }

  function openEdit(job: Job) {
    setEditing(job);
    setForm({
      customer_id: job.customer_id,
      service_type: job.service_type,
      notes: job.notes ?? "",
      status: job.status,
    });
    setError("");
    setDialogOpen(true);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const payload: JobInput = {
        customer_id: form.customer_id,
        service_type: form.service_type,
        notes: form.notes || undefined,
        status: form.status,
      };
      if (editing) {
        await api.updateJob(editing.id, payload);
      } else {
        await api.createJob(payload);
      }
      setDialogOpen(false);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save job");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(job: Job) {
    if (!confirm("Delete this job?")) return;
    await api.deleteJob(job.id);
    await loadData();
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
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Jobs</h1>
            <p className="text-muted-foreground">Track work orders and job status</p>
          </div>
          <Button onClick={openCreate}>Add job</Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>All jobs</CardTitle>
            <CardDescription>
              <div className="mt-2 flex items-center gap-2">
                <Label htmlFor="status-filter" className="sr-only">
                  Filter by status
                </Label>
                <select
                  id="status-filter"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="h-8 rounded-lg border border-input bg-background px-2 text-sm"
                >
                  <option value="">All statuses</option>
                  {JOB_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading jobs...</p>
            ) : jobs.length === 0 ? (
              <EmptyState
                title="No jobs yet"
                description="Jobs are created when the AI books appointments, or you can add one manually."
                actionLabel="Add job"
                onAction={openCreate}
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Service</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Appointment</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell>{customerMap[job.customer_id] ?? "Unknown"}</TableCell>
                      <TableCell>{job.service_type}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{job.status.replace("_", " ")}</Badge>
                      </TableCell>
                      <TableCell>
                        {job.appointment_time
                          ? formatDateTime(job.appointment_time, business?.timezone)
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" onClick={() => openEdit(job)}>
                            Edit
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => handleDelete(job)}>
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit job" : "Add job"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="customer">Customer</Label>
              <select
                id="customer"
                value={form.customer_id}
                onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                className="h-8 w-full rounded-lg border border-input bg-background px-2 text-sm"
                required
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
              <Label htmlFor="service">Service type</Label>
              <Input
                id="service"
                value={form.service_type}
                onChange={(e) => setForm({ ...form, service_type: e.target.value })}
                placeholder="e.g. Drain cleaning"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="job-status">Status</Label>
              <select
                id="job-status"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="h-8 w-full rounded-lg border border-input bg-background px-2 text-sm"
              >
                {JOB_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="job-notes">Notes</Label>
              <Textarea
                id="job-notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={3}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving || !form.customer_id || !form.service_type}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
}
