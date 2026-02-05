import type { TrendEvent } from "../App";

interface Props {
  events: TrendEvent[];
}

export function EventsPanel({ events }: Props) {
  return (
    <div className="card card-events">
      <div className="card-header">
        <h2>События и аналитика</h2>
        <p>Последние изменения цен, новости и тренды.</p>
      </div>
      <div className="events-list">
        {events.length === 0 && <p className="muted">Событий пока нет — подождите немного, агент что‑нибудь найдёт.</p>}
        {events
          .slice()
          .reverse()
          .map((ev) => (
            <div key={ev.id} className="event-item">
              <div className="event-title">{ev.title}</div>
              <div className="event-description">{ev.description}</div>
              <span className="event-chip">{ev.type}</span>
            </div>
          ))}
      </div>
    </div>
  );
}

