// Mirrors backend/app/schemas.py. Keep the two in sync.

export type SessionStatus = 'awaiting_upload' | 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed';
export type Outcome = 'success' | 'failure' | 'invalid_feed' | 'uncertain';
export type FeedMethod = 'human_feeder' | 'ball_machine';
export type Scenario = 'normal' | 'upload_error' | 'processing_error' | 'insufficient_data';

export interface Region {
  id: string;
  label: string;
}

export interface Drill {
  id: string;
  version: string;
  name: string;
  summary: string;
  purpose: string;
  stage: 'prescribed' | 'reactive';
  feed_count: number;
  max_recording_s: number;
  equipment: string[];
  starting_position: string;
  steps: string[];
  target_area: string;
  regions: Region[];
}

export interface VisionModelInfo {
  id: string;
  kind: string;
  model_id: string;
  name: string;
  owner: string;
  version: string;
  description: string;
  /** Frames leave this machine (e.g. Gemini); requires participant consent (SYS-08). */
  is_remote: boolean;
  requires_clip_file: boolean;
  sample_fps: number;
  /** "court": reports court feet itself (expected default). "image": pixels, needs the clip's saved corners. */
  output_space: 'court' | 'image';
  available: boolean;
  unavailable_reason: string | null;
  selection_mode: 'none' | 'multiple' | 'first_pose';
  requires_calibration: boolean;
}

export interface Clip {
  id: string;
  name: string;
  size_mb: number | null;
  synthetic: boolean;
  /** Court corners saved for this clip; required before it can be analyzed. */
  has_corners: boolean;
}

/** Court zones from the team's court evaluation harness (near half, left/right as seen in the image). */
export type Zone =
  | 'kitchen_left'
  | 'kitchen_right'
  | 'transition_left'
  | 'transition_right'
  | 'backcourt_left'
  | 'backcourt_right'
  | 'out_of_court'
  | 'not_visible';

/** One sampled frame, as in the harness's results.csv. Court feet: origin far-left outside corner, x 0-20, y 0-44. */
export interface CourtPoint {
  frame_index: number;
  time_s: number;
  x_px: number | null;
  y_px: number | null;
  x_ft: number | null;
  y_ft: number | null;
  zone: Zone;
  source_frame_index: number | null;
  player_id: string;
  status: string;
  reason: string | null;
  point_source: string;
}

export interface PlayerBox { x1: number; y1: number; x2: number; y2: number }
export interface AnalysisOptions {
  start_frame: number;
  max_frames: number;
  sample_fps: number;
  selections: PlayerBox[];
  calibration: { width: number; height: number; corners_px: [number, number][] };
}
export interface ClipPreview {
  source: { width: number; height: number; fps: number; frame_count: number; duration_s: number };
  frame_index: number;
  candidates: { candidate_id: number; bbox: PlayerBox; confidence: number }[];
  image_url: string;
  corners_px: [number, number][] | null;
}

export interface Session {
  analysis: AnalysisOptions | null;
  id: string;
  drill_id: string;
  drill_version: string;
  feed_method: FeedMethod;
  status: SessionStatus;
  step: number;
  progress: number;
  model_id: string | null;
  clip_id: string | null;
  clip_size_mb: number | null;
  upload_attempts: number;
  error: string | null;
  scenario: Scenario;
  steps: string[];
}

export interface Attempt {
  number: number;
  region_id: string;
  outcome: Outcome;
  reason: string | null;
  t_start_ms: number;
  t_end_ms: number;
  travel_time_s: number | null;
  response_time_s: number | null;
  lateral_ft: number | null;
  flagged: boolean;
  flag_reason: string | null;
}

export interface RegionResult {
  region_id: string;
  label: string;
  scored: number;
  successes: number;
  success_rate: number | null;
  ci_low: number | null;
  ci_high: number | null;
  avg_travel_time_s: number | null;
  sufficient: boolean;
}

export interface Results {
  session_id: string;
  drill_id: string;
  drill_name: string;
  drill_version: string;
  analysis_version: string;
  feed_method: FeedMethod;
  published: boolean;
  total_attempts: number;
  scored: number;
  successes: number;
  success_rate: number | null;
  ci_low: number | null;
  ci_high: number | null;
  avg_response_time_s: number | null;
  min_scored_per_region: number;
  sufficient: boolean;
  regions: RegionResult[];
  exclusions: { invalid_feed: number; uncertain: number; flagged: number };
  limitations: string[];
  attempts: Attempt[];
  attempts_source: 'simulated' | 'unavailable';
  track: {
    kind: string;
    model_id: string;
    model_version: string;
    sample_fps: number;
    frame_size_px: [number, number];
    frames: number;
    missing_frames: number;
    zone_counts: Partial<Record<Zone, number>>;
    data_source: 'model' | 'simulated';
    observations: number;
    players: string[];
    limitations: string[];
  };
}

export interface PublishedProfile {
  player_id: string;
  version: number;
  session_id: string;
  drill_id: string;
  drill_name: string;
  analysis_version: string;
  published_at: string;
  success_rate: number | null;
  scored: number;
  regions: RegionResult[];
}
