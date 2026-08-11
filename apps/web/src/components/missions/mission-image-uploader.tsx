"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Dropzone } from "@/components/upload/dropzone";
import { uploadMissionImage } from "@/lib/api-client";
import { qk } from "@/lib/queries";

export function MissionImageUploader({ missionId }: { missionId: string }) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(0);

  const upload = async (files: File[]) => {
    setBusy(true);
    setTotal(files.length);
    setDone(0);
    let failures = 0;
    for (const [index, file] of files.entries()) {
      setCurrent(0);
      try {
        await uploadMissionImage(missionId, file, setCurrent);
      } catch (error) {
        failures += 1;
        toast.error(`Failed to upload ${file.name}`, {
          description: error instanceof Error ? error.message : undefined,
        });
      }
      setDone(index + 1);
    }
    setBusy(false);
    // Reconcile stats + artifacts against the bucket after ingest.
    qc.invalidateQueries({ queryKey: qk.mission(missionId) });
    qc.invalidateQueries({ queryKey: qk.missionArtifacts(missionId) });
    const ok = files.length - failures;
    if (ok > 0) {
      toast.success(`${ok} image${ok === 1 ? "" : "s"} added to the mission`);
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Ingest drone images</CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-3">
        <p className="text-sm text-muted-foreground">
          Images upload directly to B2 under this mission&apos;s
          <code className="mx-1">images/</code> prefix via presigned PUT.
        </p>
        <Dropzone
          onFilesSelected={upload}
          onFilesRejected={(rejections) =>
            toast.error(`${rejections.length} file(s) rejected`)
          }
          disabled={busy}
        />
        {busy && (
          <div className="space-y-1.5">
            <Progress value={current} />
            <p className="text-xs text-muted-foreground tabular-nums">
              Uploading {done + 1} of {total}...
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
