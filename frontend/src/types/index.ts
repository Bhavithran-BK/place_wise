export interface DetectedObject {
  object_id: string;
  class: string;
  confidence: number;
  bbox: [number, number, number, number];
  mask_path?: string;
  mask_url?: string;
  action?: 'KEEP' | 'REMOVE' | 'MOVE' | null;
  fixed?: boolean;
}

export interface RoomData {
  room_id: string;
  filename: string;
  image_url: string;
  image_path?: string;
  width: number;
  height: number;
  created_at: string;
  status: 'uploaded' | 'detected' | 'instructed' | 'arranged' | 'completed';
  detected_objects: DetectedObject[];
  voice_transcript?: string | null;
  arrangement_plan?: any;
}

export interface TranscriptResult {
  success?: boolean;
  transcript: string;
  language: string;
  provider?: string;
  confidence?: number;
  words?: { word: string; start: number; end: number }[];
  source?: 'gnani_prisma' | 'google_fallback' | 'manual' | 'none';
  error?: string | null;
}

export interface ActionItem {
  object_id: string;
  object_class?: string;
  action: string;
  reason?: string;
}

export interface InstructionResult {
  success?: boolean;
  room_id?: string;
  action_plan?: {
    mode: 'REMOVE_ONLY' | 'KEEP_ONLY' | 'KEEP_AND_REMOVE' | 'REARRANGE_ALL';
    actions: ActionItem[];
    rearrange_remaining: boolean;
    clarification_required: boolean;
    clarification_message?: string | null;
    clarification_candidates?: string[];
    parsed_keep?: string[];
    parsed_remove?: string[];
    raw_transcript?: string;
  };
  mode: 'REMOVE_ONLY' | 'KEEP_ONLY' | 'KEEP_AND_REMOVE' | 'REARRANGE_ALL';
  actions: ActionItem[];
  rearrange_remaining: boolean;
  clarification_required: boolean;
  clarification_message: string | null;
  clarification_candidates?: string[];
  parsed_keep: string[];
  parsed_remove: string[];
  raw_transcript: string;
}

export type AppStep = 'upload' | 'detect' | 'voice' | 'plan' | 'result';
