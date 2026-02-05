import { useEffect, useState } from "react";
import axios from "axios";
import { ChatPanel } from "./components/ChatPanel";
import { WatchlistPanel } from "./components/WatchlistPanel";
import { EventsPanel } from "./components/EventsPanel";
import { StatusBar } from "./components/StatusBar";

export interface Game {
  id: string;
  title: string;
  source: "steam" | "epic" | "gog" | "other";
  external_id?: string | null;
  current_price?: number | null;
  original_price?: number | null;
  currency?: string | null;
  discount_percent?: number | null;
  is_tracked: boolean;
}

export interface TrendEvent {
  id: string;
  game_id?: string | null;
  type: string;
  title: string;
  description: string;
}

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [games, setGames] = useState<Game[]>([]);
  const [events, setEvents] = useState<TrendEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [watchlistRes, eventsRes] = await Promise.all([
        axios.get(`${API_BASE}/watchlist`),
        axios.get(`${API_BASE}/events?limit=20`),
      ]);
      setGames(watchlistRes.data.games ?? []);
      setEvents(eventsRes.data ?? []);
    } catch (e) {
      console.error(e);
      setError("Не удалось загрузить данные с backend. Проверь, что сервер запущен на 8000 порту.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadInitialData();
    const interval = setInterval(async () => {
      try {
        const eventsRes = await axios.get(`${API_BASE}/events?limit=50`);
        setEvents(eventsRes.data ?? []);
      } catch (e) {
        console.error(e);
      }
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const updateWatchlist = async (updatedGames: Game[]) => {
    console.log("Updating watchlist with:", updatedGames);
    setGames(updatedGames);
    try {
      const response = await axios.post(`${API_BASE}/watchlist`, { games: updatedGames });
      console.log("Watchlist saved:", response.data);
    } catch (e) {
      console.error("Error saving watchlist:", e);
      setError("Ошибка при сохранении списка игр.");
    }
  };

  return (
    <div className="app-root">
      <div className="app-gradient" />
      <header className="app-header">
        <div>
          <h1>Gaming AI Assistant</h1>
          <p className="subtitle">Игровой AI-агент аналитик (BDI)</p>
        </div>
        <button className="ghost-button" onClick={loadInitialData}>
          Обновить данные
        </button>
      </header>

      <main className="layout">
        <section className="column column-left">
          <WatchlistPanel games={games} onChange={updateWatchlist} />
          <EventsPanel events={events} />
        </section>
        <section className="column column-right">
          <ChatPanel apiBase={API_BASE} onEventsAppended={(newEvents) => setEvents((prev) => [...prev, ...newEvents])} />
        </section>
      </main>

      <StatusBar loading={loading} error={error} />
    </div>
  );
}

export default App;

