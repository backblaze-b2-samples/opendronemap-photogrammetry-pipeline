export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Missions (primary entity) ---------------------------------------------

export type QualityPreset = "draft" | "standard" | "high";
export type OutputProduct = "orthomosaic" | "dem" | "point_cloud" | "mesh";
export type MissionState =
  | "draft"
  | "queued"
  | "running"
  | "completed"
  | "failed";
export type ArtifactKind =
  | "image"
  | "orthomosaic"
  | "dem"
  | "point_cloud"
  | "mesh"
  | "texture"
  | "report"
  | "other";

export interface Artifact {
  key: string;
  filename: string;
  kind: ArtifactKind;
  size_bytes: number;
  size_human: string;
  url: string | null;
}

export interface MissionStats {
  input_count: number;
  input_bytes: number;
  input_human: string;
  output_count: number;
  output_bytes: number;
  output_human: string;
  /** output_bytes / input_bytes — the write-amplification headline. */
  amplification_ratio: number;
}

export interface MissionStatus {
  state: MissionState;
  progress: number;
  stage: string;
  task_uuid: string | null;
  error: string | null;
  updated_at: string;
}

export interface Mission {
  id: string;
  name: string;
  description: string;
  capture_date: string | null;
  quality: QualityPreset;
  products: OutputProduct[];
  dem_resolution_cm: number | null;
  image_prefix: string;
  status: MissionStatus;
  stats: MissionStats | null;
  created_at: string;
  updated_at: string;
}

export interface MissionCreate {
  name: string;
  description?: string;
  capture_date?: string | null;
  quality?: QualityPreset;
  products?: OutputProduct[];
  dem_resolution_cm?: number | null;
  image_prefix?: string | null;
}

export interface MissionUpdate {
  name?: string;
  description?: string;
  capture_date?: string | null;
  quality?: QualityPreset;
  products?: OutputProduct[];
  dem_resolution_cm?: number | null;
}

export interface DeleteMissionResponse {
  deleted: boolean;
  id: string;
  objects_deleted: number;
}
