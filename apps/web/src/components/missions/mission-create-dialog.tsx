"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
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
import { useCreateMission } from "@/lib/queries";
import {
  CREATE_DEFAULTS,
  MissionForm,
  type MissionFormValues,
  toPayload,
} from "./mission-form";

export function MissionCreateDialog() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const create = useCreateMission();

  const onSubmit = (values: MissionFormValues) => {
    create.mutate(toPayload(values), {
      onSuccess: (mission) => {
        setOpen(false);
        toast.success("Mission created", {
          description: "Upload drone images to it, then run the reconstruction.",
        });
        router.push(`/missions/${mission.id}`);
      },
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-8">
          <Plus className="h-3.5 w-3.5" />
          New mission
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New mission</DialogTitle>
          <DialogDescription>
            A mission groups a drone image set and its reconstruction outputs
            under its own B2 prefix.
          </DialogDescription>
        </DialogHeader>
        <MissionForm
          mode="create"
          defaultValues={CREATE_DEFAULTS}
          submitLabel="Create mission"
          pending={create.isPending}
          onSubmit={onSubmit}
        />
      </DialogContent>
    </Dialog>
  );
}
