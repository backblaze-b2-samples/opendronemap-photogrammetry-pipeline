"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useUpdateMission } from "@/lib/queries";
import type { Mission } from "@opendronemap-photogrammetry-pipeline/shared";
import {
  MissionForm,
  type MissionFormValues,
  toPayload,
} from "./mission-form";

function toFormValues(mission: Mission): MissionFormValues {
  return {
    name: mission.name,
    description: mission.description ?? "",
    capture_date: mission.capture_date ?? "",
    quality: mission.quality,
    products: mission.products,
    dem_resolution_cm: mission.dem_resolution_cm
      ? String(mission.dem_resolution_cm)
      : "auto",
  };
}

export function MissionEditDialog({ mission }: { mission: Mission }) {
  const [open, setOpen] = useState(false);
  const update = useUpdateMission(mission.id);
  const isActive =
    mission.status.state === "running" || mission.status.state === "queued";

  const onSubmit = (values: MissionFormValues) => {
    update.mutate(toPayload(values), {
      onSuccess: () => {
        setOpen(false);
        toast.success("Mission updated");
      },
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          disabled={isActive}
          title={isActive ? "Cannot edit while running" : undefined}
        >
          <Pencil className="h-4 w-4" />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit mission</DialogTitle>
          <DialogDescription>
            Update mission metadata and reconstruction options. Only available
            while the mission is not running.
          </DialogDescription>
        </DialogHeader>
        <MissionForm
          mode="edit"
          defaultValues={toFormValues(mission)}
          submitLabel="Save changes"
          pending={update.isPending}
          onSubmit={onSubmit}
        />
      </DialogContent>
    </Dialog>
  );
}
