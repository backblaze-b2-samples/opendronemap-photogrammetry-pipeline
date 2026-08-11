"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ArtifactGallery } from "@/components/missions/artifact-gallery";
import { DeleteMissionDialog } from "@/components/missions/delete-mission-dialog";
import { MissionEditDialog } from "@/components/missions/mission-edit-dialog";
import { MissionImageUploader } from "@/components/missions/mission-image-uploader";
import {
  MissionStatsGrid,
  MissionStatusCard,
} from "@/components/missions/mission-status-card";
import { RunMissionButton } from "@/components/missions/run-mission-button";
import { qk, useMission, useMissionStatus } from "@/lib/queries";
import type { MissionState } from "@opendronemap-photogrammetry-pipeline/shared";

const isTerminalState = (state: MissionState | undefined): boolean =>
  state === "completed" || state === "failed";

const PRODUCT_LABELS: Record<string, string> = {
  orthomosaic: "Orthomosaic",
  dem: "DEM",
  point_cloud: "Point cloud",
  mesh: "3D mesh",
};

export default function MissionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: mission, isLoading, error, refetch } = useMission(id);

  // The status query self-polls every 2s while queued/running and stops at a
  // terminal state (see `useMissionStatus`). `useMission` — which feeds the Run
  // button, stats grid, list row, and artifacts — is NOT invalidated on that
  // running→terminal edge, so it lags until an incidental refetch. Reconcile
  // the dependent queries once, on that edge, so the page reflects a finished
  // run immediately.
  const queryClient = useQueryClient();
  const { data: liveStatus } = useMissionStatus(id);
  const liveState = liveStatus?.state;
  const prevStateRef = useRef<MissionState | undefined>(undefined);

  useEffect(() => {
    const previous = prevStateRef.current;
    prevStateRef.current = liveState;
    // Fire once on the non-terminal → terminal edge (previous must be a known
    // non-terminal state, so an already-terminal first load does not refetch).
    if (previous && !isTerminalState(previous) && isTerminalState(liveState)) {
      queryClient.invalidateQueries({ queryKey: qk.mission(id) });
      queryClient.invalidateQueries({ queryKey: qk.missions() });
      queryClient.invalidateQueries({ queryKey: qk.missionArtifacts(id) });
    }
  }, [liveState, id, queryClient]);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <Link
          href="/missions"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All missions
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : mission ? (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
            <div className="min-w-0">
              <h1 className="page-title truncate">{mission.name}</h1>
              {mission.description && (
                <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
                  {mission.description}
                </p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="capitalize">
                  {mission.quality} quality
                </Badge>
                {mission.products.map((product) => (
                  <Badge key={product} variant="outline">
                    {PRODUCT_LABELS[product] ?? product}
                  </Badge>
                ))}
                {mission.capture_date && (
                  <span className="text-xs text-muted-foreground">
                    Captured {mission.capture_date}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <RunMissionButton mission={mission} />
              <MissionEditDialog mission={mission} />
              <DeleteMissionDialog mission={mission} />
            </div>
          </div>

          <MissionStatsGrid mission={mission} />
          <MissionStatusCard mission={mission} />

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="animate-fade-in-up stagger-3">
              <MissionImageUploader missionId={mission.id} />
            </div>
            <div className="animate-fade-in-up stagger-4">
              <ArtifactGallery missionId={mission.id} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
