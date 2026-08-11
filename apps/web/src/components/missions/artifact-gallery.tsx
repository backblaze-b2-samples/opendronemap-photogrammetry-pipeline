"use client";

import { useState } from "react";
import { Copy, Download, ImageIcon, Layers } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { getDownloadUrl } from "@/lib/api-client";
import { startBrowserDownload } from "@/lib/browser-download";
import { useConfig, useMissionArtifacts } from "@/lib/queries";
import type { Artifact } from "@opendronemap-photogrammetry-pipeline/shared";

const KIND_LABELS: Record<Artifact["kind"], string> = {
  image: "Input image",
  orthomosaic: "Orthomosaic",
  dem: "DEM",
  point_cloud: "Point cloud",
  mesh: "3D mesh",
  texture: "Texture",
  report: "Report",
  other: "Other",
};

export function ArtifactGallery({ missionId }: { missionId: string }) {
  const { data: artifacts = [], isLoading, error, refetch } = useMissionArtifacts(missionId);
  const { data: config } = useConfig();
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const onDownload = async (artifact: Artifact) => {
    setBusyKey(artifact.key);
    try {
      const { url } = await getDownloadUrl(artifact.key);
      if (!startBrowserDownload(url, artifact.filename)) {
        toast.error("Could not start the download");
      }
    } catch {
      toast.error("Could not fetch a download URL");
    } finally {
      setBusyKey(null);
    }
  };

  const onCopyUri = async (artifact: Artifact) => {
    const uri = config?.bucket_name
      ? `s3://${config.bucket_name}/${artifact.key}`
      : artifact.key;
    try {
      await navigator.clipboard.writeText(uri);
      toast.success("S3 URI copied", { description: uri });
    } catch {
      toast.error("Clipboard unavailable");
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <Layers className="h-4 w-4" />
          Mission artifacts
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : artifacts.length === 0 ? (
          <EmptyState
            icon={ImageIcon}
            title="No artifacts yet"
            description="Upload drone images, then run the reconstruction to generate outputs."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[44%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Artifact
                </TableHead>
                <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Kind
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Size
                </TableHead>
                <TableHead className="w-[24%] text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {artifacts.map((artifact) => (
                <TableRow key={artifact.key} className="table-row-hover">
                  <TableCell className="truncate font-medium" title={artifact.filename}>
                    {artifact.filename}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{KIND_LABELS[artifact.kind]}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {artifact.size_human}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onCopyUri(artifact)}
                      title="Copy S3 URI"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busyKey === artifact.key}
                      onClick={() => onDownload(artifact)}
                      title="Download"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </Button>
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
