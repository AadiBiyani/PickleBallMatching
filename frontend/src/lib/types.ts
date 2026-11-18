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
  name: string;
  owner: string;
  version: string;
  description: string;
  requires_clip_file: boolean;
}

export interface Clip {
  id: string;
  name: string;
  size_mb: number | null;
  synthetic: boolean;
}

export interface Session {
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
  lateral_m: number | null;
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
  track: { model_id: string; model_version: string; frames: number; missing_frames: number };
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
