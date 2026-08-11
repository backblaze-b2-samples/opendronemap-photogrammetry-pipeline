"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useMissions } from "@/lib/queries";

const chartConfig = {
  input: { label: "Input (MB)", color: "var(--chart-2)" },
  output: { label: "Output (MB)", color: "var(--chart-1)" },
} satisfies ChartConfig;

const toMb = (bytes: number) => Math.round((bytes / (1024 * 1024)) * 10) / 10;

export function AmplificationChart() {
  const { data: missions = [], isLoading, error, refetch } = useMissions();

  const data = useMemo(
    () =>
      missions
        .filter((m) => (m.stats?.output_bytes ?? 0) > 0)
        .sort((a, b) => (b.stats?.output_bytes ?? 0) - (a.stats?.output_bytes ?? 0))
        .slice(0, 6)
        .map((m) => ({
          name: m.name.length > 14 ? `${m.name.slice(0, 13)}…` : m.name,
          input: toMb(m.stats?.input_bytes ?? 0),
          output: toMb(m.stats?.output_bytes ?? 0),
        })),
    [missions],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Write amplification</CardTitle>
        <CardDescription className="text-xs">
          Input vs output bytes per reconstructed mission
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No reconstructions yet"
            description="Run a mission to see how much larger its outputs are than its inputs."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={36} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="input" fill="var(--color-input)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="output" fill="var(--color-output)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
