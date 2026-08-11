"use client";

import { CheckCircle2, HardDrive, Layers, TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { useFileStats, useMissions } from "@/lib/queries";
import { humanizeBytes } from "@/lib/utils";

export function MissionMetricCards() {
  const { data: missions = [], isLoading, error, refetch } = useMissions();
  const { data: stats } = useFileStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const completed = missions.filter((m) => m.status.state === "completed").length;
  const inputBytes = missions.reduce((sum, m) => sum + (m.stats?.input_bytes ?? 0), 0);
  const outputBytes = missions.reduce((sum, m) => sum + (m.stats?.output_bytes ?? 0), 0);
  const amplification = inputBytes > 0 ? (outputBytes / inputBytes).toFixed(1) : "—";

  const cards = [
    { title: "Missions", value: missions.length, icon: Layers },
    { title: "Completed", value: completed, icon: CheckCircle2 },
    { title: "Bucket storage", value: stats?.total_size_human ?? "0 B", icon: HardDrive },
    {
      title: "Write amplification",
      value: amplification === "—" ? "—" : `${amplification}×`,
      icon: TrendingUp,
    },
  ];

  return (
    <>
      {isLoading && <LoadingNotice className="mb-3" subject="missions" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <Card key={card.title} className={`card-hover animate-fade-in-up stagger-${i + 1}`}>
            <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className="stat-icon-wrap">
                <card.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="stat-value">{card.value}</div>
              )}
              {card.title === "Write amplification" && !isLoading && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {humanizeBytes(outputBytes)} out / {humanizeBytes(inputBytes)} in
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
