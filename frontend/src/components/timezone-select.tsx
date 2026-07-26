"use client";

import { Label } from "@/components/ui/label";
import { timezoneOptionsFor } from "@/lib/timezones";

type TimezoneSelectProps = {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
};

export function TimezoneSelect({ id = "timezone", value, onChange, hint }: TimezoneSelectProps) {
  const options = timezoneOptionsFor(value);

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>Timezone</Label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-lg border border-input bg-background px-2 text-sm"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <p className="text-xs text-muted-foreground">
        {hint ??
          "Used for calendar slots, appointment times, and reminders. Country selection sets a default at onboarding — change here if your shop uses a different local time."}
      </p>
    </div>
  );
}
