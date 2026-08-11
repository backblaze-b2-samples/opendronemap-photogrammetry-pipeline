import { Badge } from "@/components/ui/badge";
import type { MissionState } from "@opendronemap-photogrammetry-pipeline/shared";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

const STATE_META: Record<MissionState, { label: string; variant: BadgeVariant }> = {
  draft: { label: "Draft", variant: "outline" },
  queued: { label: "Queued", variant: "secondary" },
  running: { label: "Running", variant: "default" },
  completed: { label: "Completed", variant: "default" },
  failed: { label: "Failed", variant: "destructive" },
};

export function MissionStatusBadge({ state }: { state: MissionState }) {
  const meta = STATE_META[state] ?? STATE_META.draft;
  return (
    <Badge
      variant={meta.variant}
      className={
        state === "completed"
          ? "bg-[var(--success)] text-white hover:bg-[var(--success)]/90"
          : undefined
      }
    >
      {meta.label}
    </Badge>
  );
}
