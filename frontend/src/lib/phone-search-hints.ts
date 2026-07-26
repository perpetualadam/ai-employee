/** Country-specific Telnyx number search guidance for the provisioning UI. */

export function phoneSearchHint(country: string | undefined, numberType?: string): string {
  const code = (country ?? "US").toUpperCase();
  const type = (numberType ?? (code === "GB" ? "mobile" : "")).toLowerCase();

  if (code === "GB") {
    if (type === "local") {
      return "Local/geographic UK numbers (01/02…). Optional: enter a city name (e.g. London). Mobile numbers are usually better for UK SMS delivery.";
    }
    return "Searching UK mobile numbers (07…) — recommended for SMS and voice. Leave the area field empty and click Search numbers. Your Telnyx account may need UK mobile regulatory approval.";
  }

  switch (code) {
    case "US":
      return "Optional: enter a 3-digit area code (e.g. 614 for Columbus, 415 for San Francisco). Leave blank to search numbers anywhere in the US.";
    case "CA":
      return "Optional: enter a 3-digit area code (e.g. 416 for Toronto, 604 for Vancouver). Leave blank for a wider search.";
    case "AU":
      return "Optional: enter an STD area code (e.g. 02 for Sydney, 03 for Melbourne). Leave blank for a wider search.";
    case "NZ":
      return "No area filter for New Zealand — click Search numbers to browse country-wide. Telnyx may require NZ verification on your account.";
    case "IE":
      return "Optional: enter an area code (e.g. 1 for Dublin). Leave blank for a wider search.";
    case "DE":
    case "FR":
    case "NL":
    case "BE":
    case "ES":
    case "IT":
      return "Optional: enter a national destination / area code for your region. Leave blank to search more numbers in your country.";
    default:
      return "Optional prefix narrows results by area. Leave blank and click Search numbers to see what is available in your country.";
  }
}

export function telnyxBackendHint(): string {
  return "In-app search requires TELNYX_API_KEY, TELNYX_TEXML_CONNECTION_ID, and TELNYX_MESSAGING_PROFILE_ID in your server .env, then restart the API (docker compose up -d --force-recreate api).";
}
