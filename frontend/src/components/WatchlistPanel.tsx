import { useState } from "react";
import axios from "axios";
import type { Game } from "../App";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface Props {
  games: Game[];
  onChange: (games: Game[]) => void;
}

export function WatchlistPanel({ games, onChange }: Props) {
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const searchSteamGame = async (gameTitle: string) => {
    try {
      console.log("Searching for:", gameTitle);
      const response = await axios.get(`${API_BASE}/search?q=${encodeURIComponent(gameTitle)}&limit=1`);
      const results = response.data;
      console.log("Search results:", results);
      if (results && results.length > 0) {
        const game = results[0];
        console.log("Found game:", { appid: game.appid, name: game.name });
        return game; // {appid, name, price_formatted, ...}
      }
    } catch (e) {
      console.error("Error searching Steam:", e);
      // Если поиск не удался, попробуем добавить игру без external_id
      return null;
    }
    return null;
  };

  const handleAdd = async () => {
    if (!title.trim()) return;
    
    setLoading(true);
    const steamGame = await searchSteamGame(title.trim());
    setLoading(false);
    
    const id = title.toLowerCase().replace(/\s+/g, "-");
    const newGame: Game = {
      id,
      title: steamGame?.name || title.trim(),
      source: "steam",
      external_id: steamGame?.appid?.toString() || null,
      current_price: price ? Number(price) : undefined,
      currency: "RUB",
      is_tracked: true,
    };
    
    console.log("Adding game:", newGame);
    onChange([...games, newGame]);
    setTitle("");
    setPrice("");
  };

  const handleRemove = (id: string) => {
    onChange(games.filter((g) => g.id !== id));
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2>Мониторинг игр</h2>
        <p>Список игр, за которыми следит агент.</p>
      </div>
      <div className="field-row">
        <input
          className="input"
          placeholder="Название игры"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          className="input input-small"
          placeholder="Цена, ₽"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <button 
          className={`primary-button ${loading ? 'loading' : ''}`} 
          onClick={handleAdd}
          disabled={loading}
        >
          {loading ? 'Поиск...' : 'Добавить'}
        </button>
      </div>

      <div className="list">
        {games.length === 0 && <p className="muted">Пока нет отслеживаемых игр.</p>}
        {games.map((g) => (
          <div key={g.id} className="list-item">
            <div>
              <div className="game-title">{g.title}</div>
              <div className="game-meta">
                {g.current_price != null ? `${g.current_price} ${g.currency ?? "RUB"}` : "цена неизвестна"}
              </div>
            </div>
            <button className="ghost-button danger" onClick={() => handleRemove(g.id)}>
              Удалить
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

