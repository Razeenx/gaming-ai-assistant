from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class GameSource(str, Enum):
    STEAM = "steam"
    EPIC = "epic"
    GOG = "gog"
    OTHER = "other"


class Game(BaseModel):
    id: str = Field(..., description="Внутренний идентификатор игры в системе агента")
    title: str = Field(..., description="Название игры")
    source: GameSource = Field(GameSource.STEAM, description="Источник данных об игре")
    external_id: Optional[str] = Field(
        None, description="ID игры в внешнем API (Steam AppID, IGDB id и т.п.)"
    )
    current_price: Optional[float] = Field(
        None, description="Текущая цена (в условной валюте, например, рубли)"
    )
    original_price: Optional[float] = Field(
        None, description="Цена без скидки (если доступна)"
    )
    currency: Optional[str] = Field("RUB", description="Код валюты")
    discount_percent: Optional[float] = Field(
        None, description="Размер скидки в процентах, если есть"
    )
    is_tracked: bool = Field(
        True, description="Флаг: игра сейчас находится в списке мониторинга"
    )


class TrendEventType(str, Enum):
    PRICE_DROP = "price_drop"
    DISCOUNT_STARTED = "discount_started"
    DISCOUNT_ENDED = "discount_ended"
    NEW_DLC = "new_dlc"
    POPULARITY_CHANGE = "popularity_change"
    NEWS = "news"


class TrendEvent(BaseModel):
    id: str
    game_id: Optional[str] = None
    type: TrendEventType
    title: str
    description: str


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str


class ChatRequest(BaseModel):
    history: List[ChatMessage] = Field(
        default_factory=list, description="История диалога для контекста"
    )
    user_message: str = Field(..., description="Текущее сообщение пользователя")


class ChatResponse(BaseModel):
    reply: str
    events: List[TrendEvent] = Field(
        default_factory=list,
        description="Сгенерированные агентом события/рекомендации по итогам ответа",
    )


class WatchlistUpdateRequest(BaseModel):
    games: List[Game]


class WatchlistResponse(BaseModel):
    games: List[Game]

