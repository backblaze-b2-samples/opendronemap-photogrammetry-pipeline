"use client";

import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useDeleteMission } from "@/lib/queries";
import type { Mission } from "@opendronemap-photogrammetry-pipeline/shared";

export function DeleteMissionDialog({ mission }: { mission: Mission }) {
  const router = useRouter();
  const del = useDeleteMission();
  const isActive =
    mission.status.state === "running" || mission.status.state === "queued";

  const onConfirm = () => {
    del.mutate(mission.id, {
      onSuccess: (data) => {
        const count = (data as { objects_deleted?: number }).objects_deleted ?? 0;
        toast.success("Mission deleted", {
          description: `${count} object${count === 1 ? "" : "s"} removed from B2 (scoped to this mission).`,
        });
        router.push("/missions");
      },
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" disabled={isActive}>
          <Trash2 className="h-4 w-4" />
          Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this mission?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently deletes the mission manifest and every artifact
            under <code>{`missions/${mission.id}/`}</code> in B2 — inputs and
            generated outputs. The delete is scoped to this mission only. There
            is no undo.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className={buttonVariants({ variant: "destructive" })}
          >
            Yes, delete it
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
