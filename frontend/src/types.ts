export type SessionStatus = "idle" | "running" | "paused" | "error" | "stopped";
export type FragmentStatus = "queued" | "applied";

export interface ConversationTurn {
  id: string;
  session_id: string;
  speaker: string;
  visible_text: string;
  source_model: string;
  turn_index: number;
  created_at: string;
  influence_ids: string[];
  latency_ms?: number | null;
  error?: string | null;
}

export interface VisitorFragment {
  id: string;
  session_id: string;
  raw_text: string;
  normalized_text: string;
  status: FragmentStatus;
  created_at: string;
  applied_at?: string | null;
  remaining_uses: number;
  times_used: number;
}

export interface SessionRecord {
  id: string;
  status: SessionStatus;
  current_speaker: string;
  turn_index: number;
  summary_text: string;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionSnapshot {
  session: SessionRecord | null;
  turns: ConversationTurn[];
  fragments: VisitorFragment[];
}

export interface PublicConfig {
  ui: {
    title: string;
    subtitle: string;
  };
  conversation: {
    delay_seconds: number;
    context_turn_window: number;
    summary_character_limit: number;
    default_language: string;
  };
  influence: {
    max_packets_per_turn: number;
  };
  models: Record<
    string,
    {
      name: string;
      provider: string;
      model: string;
    }
  >;
}

export interface SystemEvent {
  type: string;
  session_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface DisplayEntry {
  id: string;
  kind: "turn" | "fragment";
  speaker: string;
  text: string;
  created_at: string;
  source: string;
  turnIndex?: number;
  influenceCount?: number;
  fragmentStatus?: FragmentStatus;
  fragmentUses?: number;
}
