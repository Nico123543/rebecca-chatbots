import type { PublicConfig, SessionRecord, VisitorFragment } from "../types";
import { StatusBadge } from "./StatusBadge";

interface OperatorPanelProps {
  config: PublicConfig;
  session: SessionRecord | null;
  fragments: VisitorFragment[];
  busy: boolean;
  onStart: () => Promise<void>;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
  onStop: () => Promise<void>;
}

export function OperatorPanel({
  config,
  session,
  fragments,
  busy,
  onStart,
  onPause,
  onResume,
  onStop
}: OperatorPanelProps) {
  const status = session?.status ?? "idle";

  return (
    <aside className="operator-panel">
      <div className="panel-block">
        <h2>Operator</h2>
        <div className="operator-row">
          <span>Session</span>
          <StatusBadge status={status} />
        </div>
        <div className="button-grid">
          <button onClick={onStart} disabled={busy}>
            Start fresh
          </button>
          <button onClick={onPause} disabled={busy || status !== "running"}>
            Pause
          </button>
          <button onClick={onResume} disabled={busy || status !== "paused"}>
            Resume
          </button>
          <button onClick={onStop} disabled={busy || status === "idle" || status === "stopped"}>
            Stop
          </button>
        </div>
      </div>

      <div className="panel-block">
        <h3>Models</h3>
        <ul className="info-list">
          {Object.entries(config.models).map(([key, model]) => (
            <li key={key}>
              <strong>{model.name}</strong>
              <span>{model.provider} · {model.model}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="panel-block">
        <h3>Fragment queue</h3>
        <ul className="info-list fragments-list">
          {fragments.length === 0 ? (
            <li>
              <span>No fragments yet.</span>
            </li>
          ) : (
            fragments.map((fragment) => (
              <li key={fragment.id}>
                <strong>{fragment.normalized_text}</strong>
                <span>
                  {fragment.status} · remaining {fragment.remaining_uses} · used {fragment.times_used}
                </span>
              </li>
            ))
          )}
        </ul>
      </div>
    </aside>
  );
}
