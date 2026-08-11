"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type {
  MissionCreate,
  OutputProduct,
  QualityPreset,
} from "@opendronemap-photogrammetry-pipeline/shared";

const QUALITY: QualityPreset[] = ["draft", "standard", "high"];
const PRODUCTS: { value: OutputProduct; label: string }[] = [
  { value: "orthomosaic", label: "Orthomosaic" },
  { value: "dem", label: "DEM (elevation model)" },
  { value: "point_cloud", label: "Point cloud" },
  { value: "mesh", label: "Textured 3D mesh" },
];
// DEM output resolution in cm/pixel — discrete choices only (never free text).
// "auto" is the sentinel for "no explicit resolution" (Radix forbids an
// empty-string Select item value).
const DEM_RESOLUTIONS = ["auto", "1", "2", "5", "10", "25"];

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).optional(),
  capture_date: z.string().optional(),
  quality: z.enum(["draft", "standard", "high"]),
  products: z
    .array(z.enum(["orthomosaic", "dem", "point_cloud", "mesh"]))
    .min(1, "Select at least one output product"),
  dem_resolution_cm: z.string().optional(),
});

export type MissionFormValues = z.infer<typeof schema>;

export const CREATE_DEFAULTS: MissionFormValues = {
  name: "",
  description: "",
  capture_date: "",
  quality: "standard",
  products: ["orthomosaic", "dem"],
  dem_resolution_cm: "auto",
};

/** Convert form values into a MissionCreate/MissionUpdate payload. */
export function toPayload(values: MissionFormValues): MissionCreate {
  return {
    name: values.name,
    description: values.description ?? "",
    capture_date: values.capture_date ? values.capture_date : null,
    quality: values.quality,
    products: values.products,
    dem_resolution_cm:
      values.dem_resolution_cm && values.dem_resolution_cm !== "auto"
        ? Number(values.dem_resolution_cm)
        : null,
  };
}

export function MissionForm({
  mode,
  defaultValues,
  submitLabel,
  pending,
  onSubmit,
}: {
  mode: "create" | "edit";
  defaultValues: MissionFormValues;
  submitLabel: string;
  pending: boolean;
  onSubmit: (values: MissionFormValues) => void;
}) {
  const form = useForm<MissionFormValues>({
    resolver: zodResolver(schema),
    defaultValues,
  });
  const isCreate = mode === "create";

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Mission name</FormLabel>
              <FormControl>
                <Input placeholder="e.g. north-field-2026-08" {...field} />
              </FormControl>
              {isCreate && (
                <FormDescription>
                  A short, memorable label — the site and capture date make a good one.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Optional notes about the survey"
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="capture_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Capture date</FormLabel>
              <FormControl>
                <Input type="date" className="w-52" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="quality"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Quality preset</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger className="w-60 capitalize">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {QUALITY.map((q) => (
                    <SelectItem key={q} value={q} className="capitalize">
                      {q}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {isCreate && (
                <FormDescription>
                  Draft = fastest / lowest quality — good for a first test run.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="products"
          render={() => (
            <FormItem>
              <FormLabel>Output products</FormLabel>
              <div className="grid gap-2 sm:grid-cols-2">
                {PRODUCTS.map((product) => (
                  <FormField
                    key={product.value}
                    control={form.control}
                    name="products"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center gap-2 space-y-0 rounded-md border border-border p-2.5">
                        <FormControl>
                          <Checkbox
                            checked={field.value?.includes(product.value)}
                            onCheckedChange={(checked) => {
                              const next = checked
                                ? [...field.value, product.value]
                                : field.value.filter((v) => v !== product.value);
                              field.onChange(next);
                            }}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">{product.label}</FormLabel>
                      </FormItem>
                    )}
                  />
                ))}
              </div>
              {isCreate && (
                <FormDescription>
                  Orthomosaic + DEM are a sensible default; add the point cloud and
                  mesh for full 3D deliverables.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="dem_resolution_cm"
          render={({ field }) => (
            <FormItem>
              <FormLabel>DEM resolution (cm/px)</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger className="w-60">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {DEM_RESOLUTIONS.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r === "auto" ? "Auto (engine default)" : `${r} cm/px`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end">
          <Button type="submit" disabled={pending}>
            {pending ? "Saving..." : submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}
