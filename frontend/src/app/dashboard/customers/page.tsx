"use client";

import { Plus, Search, UserPlus, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/dashboard/empty-state";
import { PageHeader } from "@/components/dashboard/page-header";
import { TablePageSkeleton } from "@/components/dashboard/page-skeletons";
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
import { Skeleton } from "@/components/ui/skeleton";
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
import { api, ApiError, Customer, CustomerInput, formatDate } from "@/lib/api";

const emptyForm: CustomerInput = {
  name: "",
  phone: "",
  email: "",
  address: "",
  notes: "",
};

export default function CustomersPage() {
  const { loading: authLoading } = useDashboardAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState<CustomerInput>(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const loadCustomers = useCallback(async (term?: string) => {
    setLoading(true);
    try {
      const data = await api.listCustomers(term);
      setCustomers(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading) loadCustomers();
  }, [authLoading, loadCustomers]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError("");
    setDialogOpen(true);
  }

  function openEdit(customer: Customer) {
    setEditing(customer);
    setForm({
      name: customer.name,
      phone: customer.phone,
      email: customer.email ?? "",
      address: customer.address ?? "",
      notes: customer.notes ?? "",
    });
    setError("");
    setDialogOpen(true);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const payload: CustomerInput = {
        name: form.name,
        phone: form.phone,
        email: form.email || undefined,
        address: form.address || undefined,
        notes: form.notes || undefined,
      };
      if (editing) {
        await api.updateCustomer(editing.id, payload);
      } else {
        await api.createCustomer(payload);
      }
      setDialogOpen(false);
      await loadCustomers(search || undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save customer");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(customer: Customer) {
    if (!confirm(`Delete ${customer.name}?`)) return;
    await api.deleteCustomer(customer.id);
    await loadCustomers(search || undefined);
  }

  if (authLoading) {
    return <TablePageSkeleton />;
  }

  return (
    <>
      <div className="space-y-6 animate-in fade-in duration-300">
        <PageHeader
          title="Customers"
          description="Manage your CRM contacts — names, numbers, and job history."
          actions={
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              Add customer
            </Button>
          }
        />

        <Card>
          <CardHeader>
            <CardTitle>All customers</CardTitle>
            <CardDescription>
              Search by name, phone, or email to find someone quickly.
            </CardDescription>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <div className="relative flex-1 sm:max-w-md">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search customers..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") loadCustomers(search || undefined);
                  }}
                  className="pl-9"
                />
              </div>
              <Button
                variant="outline"
                onClick={() => loadCustomers(search || undefined)}
              >
                Search
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full rounded-lg" />
                ))}
              </div>
            ) : customers.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No customers yet"
                description="Add your first customer manually, or let your AI receptionist capture them from calls and chats."
                actionLabel="Add customer"
                onAction={openCreate}
              />
            ) : (
              <>
                <div className="hidden overflow-x-auto md:block">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Added</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {customers.map((customer) => (
                        <TableRow key={customer.id}>
                          <TableCell className="font-medium">
                            {customer.name}
                          </TableCell>
                          <TableCell>{customer.phone}</TableCell>
                          <TableCell>{customer.email ?? "—"}</TableCell>
                          <TableCell>{formatDate(customer.created_at)}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openEdit(customer)}
                              >
                                Edit
                              </Button>
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => handleDelete(customer)}
                              >
                                Delete
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                <div className="grid gap-3 md:hidden">
                  {customers.map((customer) => (
                    <div
                      key={customer.id}
                      className="rounded-xl border border-border/80 bg-card p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{customer.name}</p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {customer.phone}
                          </p>
                          {customer.email && (
                            <p className="text-sm text-muted-foreground">
                              {customer.email}
                            </p>
                          )}
                          <p className="mt-2 text-xs text-muted-foreground">
                            Added {formatDate(customer.created_at)}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => openEdit(customer)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleDelete(customer)}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="size-4" />
              {editing ? "Edit customer" : "Add customer"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <Textarea
                id="address"
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
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
              disabled={saving || !form.name || !form.phone}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
