"use client";

import Link from "next/link";
import { ArrowRight, Layers } from "lucide-react";

import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { MissionStatusBadge } from "@/components/missions/mission-status-badge";
import { useMissions } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RecentMissionsTable() {
  const { data: missions = [], isLoading, error, refetch } = useMissions();
  const recent = missions.slice(0, 5);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent missions</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/missions"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Layers}
            title="No missions yet"
            description="Create a mission to start a reconstruction."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[42%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Mission
                </TableHead>
                <TableHead className="w-[20%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="w-[16%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Amp.
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Created
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((mission) => (
                <TableRow key={mission.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/missions/${mission.id}`}
                      className="block truncate rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                      title={mission.name}
                    >
                      {mission.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <MissionStatusBadge state={mission.status.state} />
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums whitespace-nowrap">
                    {mission.stats && mission.stats.amplification_ratio
                      ? `${mission.stats.amplification_ratio}×`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(mission.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
