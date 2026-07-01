"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CopySnippetProps {
  label: string;
  value: string;
  description?: string;
  multiline?: boolean;
}

export function CopySnippet({ label, value, description, multiline }: CopySnippetProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{label}</p>
        <Button type="button" variant="outline" size="sm" onClick={handleCopy}>
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
      <code
        className={cn(
          "block rounded bg-muted p-2 text-xs break-all",
          multiline && "whitespace-pre-wrap",
        )}
      >
        {value}
      </code>
    </div>
  );
}
