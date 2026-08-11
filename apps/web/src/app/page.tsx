import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MissionMetricCards } from "@/components/dashboard/mission-metric-cards";
import { AmplificationChart } from "@/components/dashboard/amplification-chart";
import { RecentMissionsTable } from "@/components/dashboard/recent-missions-table";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-prose">
            Drone photogrammetry on Backblaze B2 — reconstructions turn modest
            image sets into far larger orthomosaics, DEMs, point clouds, and
            meshes. These metrics show that write amplification with real bucket
            numbers.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/missions">
            <Plus className="h-3.5 w-3.5" />
            New mission
          </Link>
        </Button>
      </div>
      <MissionMetricCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <AmplificationChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentMissionsTable />
        </div>
      </div>
    </div>
  );
}
