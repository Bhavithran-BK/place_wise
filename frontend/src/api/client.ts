import type { RoomData, DetectedObject, TranscriptResult, InstructionResult } from '../types';

const API = 'http://127.0.0.1:8000';

/* ── helpers ── */
export const imgUrl = (p: string) =>
  !p ? '' : p.startsWith('http') ? p : `${API}${p}`;

export const getFullImageUrl = imgUrl;

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail ?? 'Request failed');
  }
  return res.json();
}

/* ── rooms ── */
export const uploadRoom = async (file: File): Promise<RoomData> => {
  const fd = new FormData();
  fd.append('file', file);
  const data = await json<any>(await fetch(`${API}/api/rooms`, { method: 'POST', body: fd }));
  return {
    ...data,
    detected_objects: data.detected_objects || [],
  };
};

export const getRoom = async (id: string): Promise<RoomData> =>
  json(await fetch(`${API}/api/rooms/${id}`));

/* ── vision ── */
export const detectObjects = async (
  id: string,
): Promise<{ objects: DetectedObject[] }> =>
  json(await fetch(`${API}/api/rooms/${id}/detect`, { method: 'POST' }));

export const patchObjects = async (
  id: string,
  updates: {
    object_id: string;
    class_name?: string;
    action?: string | null;
    fixed?: boolean;
  }[],
) =>
  json(
    await fetch(`${API}/api/rooms/${id}/objects`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    }),
  );

/* ── voice ── */
export const transcribeAudio = async (
  id: string,
  audioBlob: Blob,
): Promise<TranscriptResult> => {
  const fd = new FormData();
  fd.append('file', audioBlob, 'recording.wav');
  return json(await fetch(`${API}/api/rooms/${id}/transcribe`, { method: 'POST', body: fd }));
};

export const transcribeText = async (
  id: string,
  text: string,
): Promise<TranscriptResult> =>
  json(
    await fetch(`${API}/api/rooms/${id}/transcribe-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  );

export const parseInstructions = async (
  id: string,
  transcript: string,
): Promise<InstructionResult> => {
  const data = await json<any>(
    await fetch(`${API}/api/rooms/${id}/instructions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript }),
    }),
  );
  const plan = data.action_plan || data;
  return {
    ...data,
    mode: plan.mode || data.mode || 'REARRANGE_ALL',
    actions: plan.actions || data.actions || [],
    rearrange_remaining: plan.rearrange_remaining ?? data.rearrange_remaining ?? false,
    clarification_required: plan.clarification_required ?? data.clarification_required ?? false,
    clarification_message: plan.clarification_message ?? data.clarification_message ?? null,
    clarification_candidates: plan.clarification_candidates ?? data.clarification_candidates ?? [],
    parsed_keep: plan.parsed_keep ?? data.parsed_keep ?? [],
    parsed_remove: plan.parsed_remove ?? data.parsed_remove ?? [],
    raw_transcript: plan.raw_transcript || data.raw_transcript || transcript,
  };
};

export const speakConfirmation = async (
  id: string,
  text?: string,
): Promise<{ text: string; audio_url: string | null; source: string }> =>
  json(
    await fetch(`${API}/api/rooms/${id}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  );

/* ── arrangement & rendering ── */
export const arrangeRoom = async (id: string): Promise<any> =>
  json(await fetch(`${API}/api/rooms/${id}/arrange`, { method: 'POST' }));

export const renderOutputs = async (
  id: string,
): Promise<{ status: string; plan_image_url: string; rearranged_image_url: string; plan: any }> =>
  json(await fetch(`${API}/api/rooms/${id}/render`, { method: 'POST' }));

export const getResults = async (id: string): Promise<any> =>
  json(await fetch(`${API}/api/rooms/${id}/results`));

/* ── health ── */
export const checkHealth = async (): Promise<boolean> => {
  try {
    const r = await fetch(`${API}/api/health`);
    return r.ok;
  } catch {
    return false;
  }
};
