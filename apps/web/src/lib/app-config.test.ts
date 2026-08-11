import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("OpenDroneMap Photogrammetry Pipeline");
    expect(APP_DESCRIPTION).toBe(
      "Drone photogrammetry pipeline — orthomosaics, DEMs, point clouds & 3D meshes on Backblaze B2"
    );
  });
});
