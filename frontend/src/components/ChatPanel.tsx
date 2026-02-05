import { useEffect, useRef, useState } from "react";
import axios from "axios";
import type { TrendEvent } from "../App";

interface Props {
  apiBase: string;
  onEventsAppended: (events: TrendEvent[]) => void;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function ChatPanel({ apiBase, onEventsAppended }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Привет! Я игровой AI‑агент. Задай вопрос про игры, скидки или тренды. 🎮",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    const newMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setInput("");
    setSending(true);

    try {
      const historyPayload = newMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const res = await axios.post(`${apiBase}/chat`, {
        history: historyPayload.slice(0, -1),
        user_message: text,
      });

      const reply: string = res.data.reply;
      const events: TrendEvent[] = res.data.events ?? [];
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      if (events.length) {
        onEventsAppended(events);
      }
    } catch (e) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Произошла ошибка при обращении к backend. Проверь, что сервер запущен.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="card card-chat">
      <div className="card-header">
        <h2>Чат с агентом</h2>
        <p>Спроси про игры, скидки или рекомендации.</p>
      </div>

      <div className="chat-window" ref={scrollRef}>
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-message chat-message-${m.role}`}>
            <div className="chat-avatar">{m.role === "assistant" ? "AI" : "Ты"}</div>
            <div className="chat-bubble">{m.content}</div>
          </div>
        ))}
      </div>

      <div className="chat-input-row">
        <textarea
          className="input chat-input"
          rows={2}
          placeholder="Напиши сообщение и нажми Enter..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="primary-button" disabled={sending} onClick={handleSend}>
          {sending ? "Отправка..." : "Отправить"}
        </button>
      </div>

      <div className="quick-actions">
        <span className="muted">Быстрые действия:</span>
        <button
          className="chip-button"
          onClick={() => setInput("Покажи игры с самыми большими скидками")}
        >
          Скидки
        </button>
        <button
          className="chip-button"
          onClick={() => setInput("Что сейчас популярно среди RPG?")}
        >
          Тренды RPG
        </button>
        <button
          className="chip-button"
          onClick={() => setInput("Стоит ли сейчас покупать мои игры из мониторинга?")}
        >
          Стоит ли покупать?
        </button>
      </div>
    </div>
  );
}

