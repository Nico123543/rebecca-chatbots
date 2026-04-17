import { useEffect, useRef, useState } from "react";
import { ConversationFeed } from "./components/ConversationFeed";
import { FragmentInput } from "./components/FragmentInput";
import { OperatorPanel } from "./components/OperatorPanel";
import { StatusBadge } from "./components/StatusBadge";
import { api, openSessionStream } from "./lib/api";
import type { DisplayEntry, PublicConfig, SessionSnapshot, SystemEvent } from "./types";

type ViewMode = "kiosk" | "operator";

const fallbackConfig: PublicConfig = {
  ui: {
    title: "Reciprocal Drift",
    subtitle: "Two models loop until a visitor tilts the orbit."
  },
  conversation: {
    delay_seconds: 3,
    context_turn_window: 10,
    summary_character_limit: 1200,
    default_language: "en"
  },
  influence: {
    max_packets_per_turn: 1
  },
  models: {}
};

export default function App() {
  const [config, setConfig] = useState<PublicConfig>(fallbackConfig);
  const [snapshot, setSnapshot] = useState<SessionSnapshot>({
    session: null,
    turns: [],
    fragments: []
  });
  const [viewMode, setViewMode] = useState<ViewMode>("kiosk");
  const [busy, setBusy] = useState(false);
  const [connectionState, setConnectionState] = useState("disconnected");
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const displayEntries: DisplayEntry[] = [...snapshot.turns, ...snapshot.fragments]
    .map((item) => {
      if ("visible_text" in item) {
        return {
          id: item.id,
          kind: "turn" as const,
          speaker: item.speaker,
          text: item.visible_text,
          created_at: item.created_at,
          source: item.source_model,
          turnIndex: item.turn_index,
          influenceCount: item.influence_ids.length
        };
      }
      return {
        id: item.id,
        kind: "fragment" as const,
        speaker: "visitor_interject",
        text: item.normalized_text,
        created_at: item.created_at,
        source: "visitor interject",
        fragmentStatus: item.status,
        fragmentUses: item.times_used
      };
    })
    .sort((left, right) => {
      const timeDelta =
        new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
      if (timeDelta !== 0) {
        return timeDelta;
      }
      return left.id.localeCompare(right.id);
    });

  async function refresh() {
    const [nextConfig, nextSnapshot] = await Promise.all([
      api.getConfig(),
      api.getCurrentSession()
    ]);
    setConfig(nextConfig);
    setSnapshot(nextSnapshot);
  }

  useEffect(() => {
    refresh().catch((caught) => setError((caught as Error).message));
  }, []);

  useEffect(() => {
    const sessionId = snapshot.session?.id;
    socketRef.current?.close();
    if (!sessionId) {
      setConnectionState("idle");
      return;
    }
    setConnectionState("connecting");
    const socket = openSessionStream(sessionId, (event) => {
      applyEvent(event);
    });
    socketRef.current = socket;
    socket.onopen = () => {
      setConnectionState("live");
      refresh().catch((caught) => setError((caught as Error).message));
    };
    socket.onerror = () => setConnectionState("error");
    socket.onclose = () => setConnectionState("disconnected");
    return () => socket.close();
  }, [snapshot.session?.id]);

  useEffect(() => {
    if (!snapshot.session || snapshot.session.status !== "running") {
      return;
    }
    const timer = window.setInterval(() => {
      refresh().catch((caught) => setError((caught as Error).message));
    }, 1500);
    return () => window.clearInterval(timer);
  }, [snapshot.session?.id, snapshot.session?.status]);

  function applyEvent(event: SystemEvent) {
    setSnapshot((current) => {
      const next: SessionSnapshot = {
        session: current.session,
        turns: [...current.turns],
        fragments: [...current.fragments]
      };
      const payload = event.payload as {
        session?: SessionSnapshot["session"];
        turn?: SessionSnapshot["turns"][number];
        fragment?: SessionSnapshot["fragments"][number];
      };

      if (payload.session) {
        next.session = payload.session;
      }
      if (payload.turn) {
        const existingIndex = next.turns.findIndex((turn) => turn.id === payload.turn?.id);
        if (existingIndex >= 0) {
          next.turns[existingIndex] = payload.turn;
        } else {
          next.turns.push(payload.turn);
        }
      }
      if (payload.fragment) {
        const existingIndex = next.fragments.findIndex(
          (fragment) => fragment.id === payload.fragment?.id
        );
        if (existingIndex >= 0) {
          next.fragments[existingIndex] = payload.fragment;
        } else {
          next.fragments.push(payload.fragment);
        }
      }
      return next;
    });
  }

  async function runAction(action: () => Promise<SessionSnapshot>) {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setSnapshot(next);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleFullscreen() {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  }

  return (
    <div className={`app-shell mode-${viewMode}`}>
      <header className="app-header">
        <div>
          <p className="eyebrow">Local kiosk installation</p>
          <h1>{config.ui.title}</h1>
          <p className="subtitle">{config.ui.subtitle}</p>
        </div>
        <div className="header-controls">
          <div className="view-toggle">
            <button
              className={viewMode === "kiosk" ? "active" : ""}
              onClick={() => setViewMode("kiosk")}
            >
              Kiosk
            </button>
            <button
              className={viewMode === "operator" ? "active" : ""}
              onClick={() => setViewMode("operator")}
            >
              Operator
            </button>
          </div>
          <div className="connection-pill">{connectionState}</div>
          <button className="ghost-button" onClick={toggleFullscreen}>
            Fullscreen
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <main className="app-grid">
        <section className="kiosk-panel">
          <div className="kiosk-topline">
            <div>
              <span className="panel-label">Conversation</span>
              <StatusBadge status={snapshot.session?.status ?? "idle"} />
            </div>
            <span className="session-note">
              {snapshot.session
                ? `Turn ${snapshot.session.turn_index} · next ${snapshot.session.current_speaker}`
                : "No active session"}
            </span>
          </div>

          <ConversationFeed entries={displayEntries} />

          <FragmentInput
            disabled={
              !snapshot.session ||
              snapshot.session.status === "stopped" ||
              snapshot.session.status === "error"
            }
            onSubmit={(text) => runAction(() => api.sendFragment(text))}
          />
        </section>

        <OperatorPanel
          config={config}
          session={snapshot.session}
          fragments={snapshot.fragments}
          busy={busy}
          onStart={() => runAction(() => api.startSession())}
          onPause={() => runAction(() => api.pauseSession())}
          onResume={() => runAction(() => api.resumeSession())}
          onStop={() => runAction(() => api.stopSession())}
        />
      </main>
    </div>
  );
}
