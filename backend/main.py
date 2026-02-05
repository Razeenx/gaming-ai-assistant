from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from typing import Any, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .agent.bdi_agent import agent
from .services.steam_service import steam_service
from .services.cheapshark_service import cheapshark_service
from .services.epic_service import epic_service
from .services.gog_service import gog_service
from .services.humble_service import humble_service
from .services.ai_service import is_available as ai_available
from .models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Game,
    TrendEvent,
    WatchlistResponse,
    WatchlistUpdateRequest,
)

app = FastAPI(
    title="Gaming AI Assistant",
    description="Игровой AI-агент аналитик (BDI) для мониторинга игр и цен. "
                "Использует Steam Store API и CheapShark API для реальных данных.",
    version="0.2.0",
)

# Разрешаем доступ для React-клиента
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    # Запускаем фоновый мониторинг каждые 180 секунд (3 минуты), чтобы не блокировать Steam API
    asyncio.create_task(agent.start_monitoring(interval_seconds=180))


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке."""
    await steam_service.close()
    await cheapshark_service.close()
    await epic_service.close()
    await gog_service.close()
    await humble_service.close()


# === Базовые endpoints ===

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "0.3.0",
        "ai_available": ai_available(),
    }


# === Watchlist (мониторинг игр) ===

@app.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist() -> WatchlistResponse:
    """Получить список отслеживаемых игр."""
    games: List[Game] = agent.get_watchlist()
    return WatchlistResponse(games=games)


@app.post("/watchlist", response_model=WatchlistResponse)
async def update_watchlist(req: WatchlistUpdateRequest) -> WatchlistResponse:
    """Обновить список отслеживаемых игр."""
    games = agent.apply_watchlist(req.games)
    
    # Принудительно обновляем данные об играх
    await agent._update_watchlist_prices()
    
    return WatchlistResponse(games=games)


# === События ===

@app.get("/events", response_model=list[TrendEvent])
async def get_events(limit: int = 20) -> List[TrendEvent]:
    """Получить последние события (скидки, изменения цен, новости)."""
    return agent.get_recent_events(limit=limit)


# === Чат с агентом ===

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Чат с AI-агентом. Понимает запросы о скидках, поиске игр, сравнении цен."""
    messages: List[ChatMessage] = req.history + [
        ChatMessage(role="user", content=req.user_message)
    ]
    return await agent.chat(messages)


# === Поиск игр (Steam) ===

@app.get("/search")
async def search_games(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=25, description="Количество результатов"),
) -> List[dict[str, Any]]:
    """
    Поиск игр по названию через Steam Store API.
    
    Возвращает список с appid, названием и ценой.
    """
    return await steam_service.search_games(q, limit=limit)


@app.get("/game/{appid}")
async def get_game_details(appid: int) -> Optional[dict[str, Any]]:
    """
    Получить детальную информацию об игре из Steam по AppID.
    
    Включает цены, жанры, описание, рейтинг Metacritic и др.
    """
    return await steam_service.get_app_details(appid)


# === Скидки и акции ===

@app.get("/deals/steam")
async def get_steam_specials(
    limit: int = Query(20, ge=1, le=50, description="Количество результатов"),
) -> List[dict[str, Any]]:
    """
    Получить текущие скидки в Steam.
    
    Данные из Steam Store API, цены в рублях.
    """
    return await steam_service.get_specials(limit=limit)


@app.get("/deals/featured")
async def get_featured_games() -> List[dict[str, Any]]:
    """Получить рекомендуемые игры Steam."""
    return await steam_service.get_featured()


@app.get("/deals/top")
async def get_top_deals(
    limit: int = Query(15, ge=1, le=30, description="Количество результатов"),
) -> List[dict[str, Any]]:
    """
    Топ скидок со всех площадок (CheapShark API).
    
    Включает Steam, GOG, Epic, Humble и другие магазины.
    Цены в USD.
    """
    return await cheapshark_service.get_top_deals(limit=limit)


@app.get("/deals/all")
async def get_all_deals(
    store: Optional[str] = Query(None, description="ID магазина (1=Steam, 7=GOG, 25=Epic)"),
    max_price: Optional[float] = Query(None, description="Макс. цена (USD)"),
    min_metacritic: Optional[int] = Query(None, description="Мин. рейтинг Metacritic"),
    limit: int = Query(20, ge=1, le=50),
) -> List[dict[str, Any]]:
    """
    Гибкий поиск скидок с фильтрами (CheapShark API).
    
    Можно фильтровать по магазину, цене и рейтингу.
    """
    return await cheapshark_service.get_deals(
        store_id=store,
        upper_price=max_price,
        min_metacritic=min_metacritic,
        limit=limit,
    )


@app.get("/deals/free")
async def get_free_games(
    limit: int = Query(10, ge=1, le=20),
) -> List[dict[str, Any]]:
    """Получить бесплатные игры."""
    return await cheapshark_service.get_free_games(limit=limit)


# === Сравнение цен ===

@app.get("/compare")
async def compare_prices(
    title: str = Query(..., min_length=2, description="Название игры"),
) -> Optional[dict[str, Any]]:
    """
    Сравнить цены на игру на разных площадках (CheapShark API).
    
    Показывает текущие предложения во всех магазинах и историческое дно цены.
    """
    return await agent.compare_prices(title)


# === Информация о магазинах ===

@app.get("/stores")
async def get_stores() -> List[dict[str, Any]]:
    """Список поддерживаемых магазинов (CheapShark)."""
    return await cheapshark_service.get_stores()
