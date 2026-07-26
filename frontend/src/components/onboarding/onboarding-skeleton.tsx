import { Skeleton } from "@/components/ui/skeleton";

export function OnboardingSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 px-4 py-8 animate-in fade-in duration-300">
      <div className="space-y-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-2 w-full rounded-full" />
        <div className="hidden gap-2 sm:grid sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-16 rounded-lg" />
          ))}
        </div>
      </div>
      <Skeleton className="h-[420px] rounded-xl" />
    </div>
  );
}
