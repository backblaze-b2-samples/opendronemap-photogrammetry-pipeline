"use client";

import { AlertTriangle, ArrowUpFromLine, HardDrive, Layers, TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useMissionStatus } from "@/lib/queries";
import type { Mission } from "@opendronemap-photogrammetry-pipeline/shared";
import { MissionStatusBadge } from "./mission-status-badge";

export function MissionStatusCard({ mission }: { mission: Mission }) {
  // Poll live status; falls back to the mission's persisted status.
  const { data } = useMissionStatus(mission.id);
  const status = data ?? mission.status;
  const active = status.state === "running" || status.state === "queued";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border py-4 px-5">
        <CardTitle className="card-title">Reconstruction status</CardTitle>
        <MissionStatusBadge state={status.state} />
      </CardHeader>
      <CardContent className="p-5 space-y-3">
        <p className="text-sm text-muted-foreground">{status.stage || "—"}</p>
        {active && (
          <div className="space-y-1.5">
            <Progress value={status.progress} />
            <p className="text-xs text-muted-foreground tabular-nums">
              {Math.round(status.progress)}%
            </p>
          </div>
        )}
        {status.state === "failed" && status.error && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="[overflow-wrap:anywhere]">{status.error}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function MissionStatsGrid({ mission }: { mission: Mission }) {
  const stats = mission.stats;
  const cards = [
    { title: "Input images", value: stats?.input_count ?? 0, sub: stats?.input_human ?? "0 B", icon: Layers },
    { title: "Output artifacts", value: stats?.output_count ?? 0, sub: stats?.output_human ?? "0 B", icon: HardDrive },
    { title: "Input size", value: stats?.input_human ?? "0 B", sub: "drone JPEGs", icon: ArrowUpFromLine },
    {
      title: "Write amplification",
      value: stats && stats.amplification_ratio ? `${stats.amplification_ratio}×` : "—",
      sub: "output ÷ input bytes",
      icon: TrendingUp,
    },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title} className="card-hover">
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            <div className="stat-value">{card.value}</div>
            <p className="mt-1 text-xs text-muted-foreground">{card.sub}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
