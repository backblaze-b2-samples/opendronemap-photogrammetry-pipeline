import { MissionCreateDialog } from "@/components/missions/mission-create-dialog";
import { MissionTable } from "@/components/missions/mission-table";

export default function MissionsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Missions</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Each mission ingests a drone image set into B2 and reconstructs it
            into orthomosaics, DEMs, point clouds, and 3D meshes. Outputs are
            typically several times larger than the inputs — the write
            amplification column shows the ratio.
          </p>
        </div>
        <MissionCreateDialog />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <MissionTable />
      </div>
    </div>
  );
}
