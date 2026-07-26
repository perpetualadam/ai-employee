import type { LucideIcon } from "lucide-react";
import {
  Building2,
  Phone,
  Rocket,
  Sparkles,
  Wrench,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface OnboardingStep {
  title: string;
  description: string;
  icon: LucideIcon;
}

export const onboardingSteps: OnboardingStep[] = [
  {
    title: "Welcome",
    description: "Let's set up your AI employee",
    icon: Sparkles,
  },
  {
    title: "Business",
    description: "Tell us about your company",
    icon: Building2,
  },
  {
    title: "Services",
    description: "What jobs do you take?",
    icon: Wrench,
  },
  {
    title: "Phone",
    description: "Connect your phone line",
    icon: Phone,
  },
  {
    title: "Go live",
    description: "Test and launch",
    icon: Rocket,
  },
];

interface OnboardingProgressProps {
  currentStep: number;
  className?: string;
}

export function OnboardingProgress({
  currentStep,
  className,
}: OnboardingProgressProps) {
  const progress = ((currentStep + 1) / onboardingSteps.length) * 100;

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Step {currentStep + 1} of {onboardingSteps.length}
          </p>
          <p className="font-heading text-lg font-semibold">
            {onboardingSteps[currentStep]?.title}
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
          {Math.round(progress)}%
        </span>
      </div>

      <div
        className="h-2 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={Math.round(progress)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Setup progress"
      >
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <ol className="hidden gap-2 sm:grid sm:grid-cols-5">
        {onboardingSteps.map((step, index) => {
          const Icon = step.icon;
          const isComplete = index < currentStep;
          const isCurrent = index === currentStep;

          return (
            <li
              key={step.title}
              className={cn(
                "rounded-lg border px-2 py-2 text-center transition-colors",
                isCurrent && "border-primary/40 bg-primary/5",
                isComplete && "border-success/30 bg-success/5",
                !isCurrent && !isComplete && "border-transparent bg-muted/40",
              )}
            >
              <div
                className={cn(
                  "mx-auto mb-1 flex size-7 items-center justify-center rounded-full",
                  isCurrent && "bg-primary text-primary-foreground",
                  isComplete && "bg-success text-success-foreground",
                  !isCurrent && !isComplete && "bg-muted text-muted-foreground",
                )}
              >
                <Icon className="size-3.5" aria-hidden />
              </div>
              <p className="truncate text-[0.65rem] font-medium">{step.title}</p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
