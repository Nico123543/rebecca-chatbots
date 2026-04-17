import type { DisplayEntry } from "../types";

interface ConversationFeedProps {
  entries: DisplayEntry[];
}

export function ConversationFeed({ entries }: ConversationFeedProps) {
  if (entries.length === 0) {
    return (
      <div className="empty-state">
        <p>No conversation yet.</p>
        <span>Start a session to let the loop begin.</span>
      </div>
    );
  }

  return (
    <div className="conversation-feed">
      {entries.map((entry) => (
        <article key={entry.id} className={`turn-card speaker-${entry.speaker}`}>
          <header>
            <span className="speaker-label">{entry.speaker.replace("_", " ")}</span>
            <span className="turn-meta">
              {entry.kind === "turn" && entry.turnIndex !== undefined
                ? `#${entry.turnIndex + 1} · `
                : ""}
              {new Date(entry.created_at).toLocaleTimeString()}
            </span>
          </header>
          <p>{entry.text}</p>
          <footer>
            <span>{entry.source}</span>
            {entry.kind === "turn" ? (
              (entry.influenceCount ?? 0) > 0 ? (
                <span>{entry.influenceCount} fragment influence</span>
              ) : (
                <span>self-propelled turn</span>
              )
            ) : (
              <span>
                {entry.fragmentStatus} · used {entry.fragmentUses ?? 0}
              </span>
            )}
          </footer>
        </article>
      ))}
    </div>
  );
}
