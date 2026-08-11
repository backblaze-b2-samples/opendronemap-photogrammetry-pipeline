"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";

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
import { useMission } from "@/lib/queries";

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
