"use client";

import { Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useRunMission } from "@/lib/queries";
import type { Mission } from "@opendronemap-photogrammetry-pipeline/shared";

export function RunMissionButton({ mission }: { mission: Mission }) {
  const run = useRunMission(mission.id);
  const isActive =
    mission.status.state === "running" || mission.status.state === "queued";
  const hasImages = (mission.stats?.input_count ?? 0) > 0;

  const onClick = () => {
    run.mutate(undefined, {
      onSuccess: () => toast.success("Reconstruction queued"),
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <Button
      onClick={onClick}
      disabled={run.isPending || isActive || !hasImages}
      title={!hasImages ? "Upload drone images before running" : undefined}
    >
      <Play className="h-4 w-4" />
      {isActive ? "Reconstruction running" : "Run reconstruction"}
    </Button>
  );
}
