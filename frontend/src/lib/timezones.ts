/** Common IANA timezones for trade businesses — calendar and voice slot times use this. */

export type TimezoneOption = {
  value: string;
  label: string;
};

export const TIMEZONE_OPTIONS: TimezoneOption[] = [
  { value: "America/New_York", label: "Eastern — US & Canada (New York)" },
  { value: "America/Chicago", label: "Central — US & Canada (Chicago)" },
  { value: "America/Denver", label: "Mountain — US (Denver)" },
  { value: "America/Phoenix", label: "Arizona — US (no DST)" },
  { value: "America/Los_Angeles", label: "Pacific — US & Canada (Los Angeles)" },
  { value: "America/Anchorage", label: "Alaska" },
  { value: "Pacific/Honolulu", label: "Hawaii" },
  { value: "America/Toronto", label: "Canada — Eastern (Toronto)" },
  { value: "America/Vancouver", label: "Canada — Pacific (Vancouver)" },
  { value: "America/Halifax", label: "Canada — Atlantic (Halifax)" },
  { value: "America/Winnipeg", label: "Canada — Central (Winnipeg)" },
  { value: "Europe/London", label: "United Kingdom (London)" },
  { value: "Europe/Dublin", label: "Ireland (Dublin)" },
  { value: "Europe/Paris", label: "France (Paris)" },
  { value: "Europe/Berlin", label: "Germany (Berlin)" },
  { value: "Europe/Amsterdam", label: "Netherlands (Amsterdam)" },
  { value: "Europe/Brussels", label: "Belgium (Brussels)" },
  { value: "Europe/Madrid", label: "Spain (Madrid)" },
  { value: "Europe/Rome", label: "Italy (Rome)" },
  { value: "Europe/Stockholm", label: "Sweden (Stockholm)" },
  { value: "Europe/Copenhagen", label: "Denmark (Copenhagen)" },
  { value: "Europe/Warsaw", label: "Poland (Warsaw)" },
  { value: "Europe/Athens", label: "Greece (Athens)" },
  { value: "Australia/Sydney", label: "Australia — Eastern (Sydney)" },
  { value: "Australia/Melbourne", label: "Australia — Eastern (Melbourne)" },
  { value: "Australia/Brisbane", label: "Australia — Queensland (Brisbane)" },
  { value: "Australia/Perth", label: "Australia — Western (Perth)" },
  { value: "Australia/Adelaide", label: "Australia — Central (Adelaide)" },
  { value: "Pacific/Auckland", label: "New Zealand (Auckland)" },
];

/** Include the business timezone if it is not in the preset list (legacy/custom values). */
export function timezoneOptionsFor(current?: string): TimezoneOption[] {
  const normalized = (current ?? "").trim();
  if (!normalized) return TIMEZONE_OPTIONS;
  if (TIMEZONE_OPTIONS.some((opt) => opt.value === normalized)) {
    return TIMEZONE_OPTIONS;
  }
  return [{ value: normalized, label: `${normalized} (current)` }, ...TIMEZONE_OPTIONS];
}
