import type {
  Clip,
  CourtPoint,
  Drill,
  FeedMethod,
  PublishedProfile,
  Results,
  Scenario,
  Session,
  VisionModelInfo,
} from './types';

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: init?.method ?? 'GET',
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
      body: init?.body ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError(0, `Can't reach the analysis server at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  drills: () => request<Drill[]>('/api/drills'),
  models: () => request<VisionModelInfo[]>('/api/models'),
  clips: () => request<Clip[]>('/api/clips'),
  profile: () => request<PublishedProfile | null>('/api/profile'),

  createSession: (body: {
    drill_id: string;
    drill_version: string;
    feed_method: FeedMethod;
    capture_started_at: string;
    capture_ended_at: string;
    scenario: Scenario;
  }) => request<Session>('/api/sessions', { method: 'POST', body }),
  session: (id: string) => request<Session>(`/api/sessions/${id}`),
  upload: (id: string, body: { model_id: string; clip_id: string }) =>
    request<Session>(`/api/sessions/${id}/upload`, { method: 'POST', body }),
  results: (id: string) => request<Results>(`/api/sessions/${id}/results`),
  track: (id: string) => request<CourtPoint[]>(`/api/sessions/${id}/track`),
  flag: (id: string, number: number, reason: string) =>
    request<Results>(`/api/sessions/${id}/attempts/${number}/flag`, { method: 'POST', body: { reason } }),
  publish: (id: string) => request<PublishedProfile>(`/api/sessions/${id}/publish`, { method: 'POST' }),

  debugSession: (state: 'awaiting_upload' | 'processing' | 'completed' | 'failed' | 'published', scenario: Scenario = 'normal') =>
    request<Session>('/api/debug/sessions', { method: 'POST', body: { state, scenario } }),
  debugReset: () => request<void>('/api/debug/reset', { method: 'POST' }),
};
