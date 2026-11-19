import { api, ApiError } from './api';

export type UploadOutcome = { ok: true } | { ok: false; retryable: boolean; message: string };

/**
 * Dummy upload: asks the backend to send the chosen pre-recorded clip to the
 * selected vision model. Network/server failures are retryable under the same
 * session ID (FR-07); 4xx errors are configuration problems.
 */
export async function uploadSession(
  sessionId: string,
  modelId: string,
  clipId: string,
  consentConfirmed = false,
): Promise<UploadOutcome> {
  try {
    await api.upload(sessionId, { model_id: modelId, clip_id: clipId, consent_confirmed: consentConfirmed });
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError) {
      return { ok: false, retryable: e.status === 0 || e.status >= 500, message: e.message };
    }
    return { ok: false, retryable: true, message: String(e) };
  }
}
