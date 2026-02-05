from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import (
    ChatMessage,
    ChatResponse,
    Game,
    GameSource,
    TrendEvent,
    TrendEventType,
)
from ..services.steam_service import steam_service
from ..services.cheapshark_service import cheapshark_service
from ..services.epic_service import epic_service
from ..services.gog_service import gog_service
from ..services.humble_service import humble_service
from ..services.ai_service import is_available as groq_available, chat_completion as groq_chat


@dataclass
class Beliefs:
    """Убеждения агента: что он знает о мире сейчас."""

    games: Dict[str, Game] = field(default_factory=dict)
    events: List[TrendEvent] = field(default_factory=list)
    # Кэш последних данных из API
    last_steam_specials: List[dict] = field(default_factory=list)
    last_top_deals: List[dict] = field(default_factory=list)
    last_update: Optional[datetime] = None


@dataclass
class Desire:
    """Желание агента: чего он хочет достичь."""

    description: str
    priority: int = 1  # 1 = высший приоритет


@dataclass
class Intention:
    """Намерение: конкретный план действий."""

    description: str
    action: str  # Идентификатор действия


class GamingBDIAgent:
    """
    BDI-агент для игровой аналитики с реальными API.

    Использует:
    - Steam Store API для информации о играх и ценах
    - CheapShark API для сравнения цен на разных площадках
    """

    def __init__(self) -> None:
        self.beliefs = Beliefs()
        self.desires: List[Desire] = []
        self.intentions: List[Intention] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._event_counter = 0

    def _generate_event_id(self) -> str:
        # Используем только UUID для полной уникальности
        return f"event_{uuid.uuid4().hex}"

    # === BDI-цикл ===

    def update_beliefs_from_watchlist(self, games: List[Game]) -> None:
        """Обновление убеждений на основе списка отслеживаемых игр."""
        for game in games:
            self.beliefs.games[game.id] = game

    def generate_desires(self) -> None:
        """Формирование желаний: что агент хочет сделать."""
        self.desires = [
            Desire(description="Обновить цены отслеживаемых игр из Steam", priority=1),
            Desire(description="Найти лучшие скидки на рынке", priority=2),
            Desire(description="Сравнить цены на разных площадках", priority=2),
            Desire(description="Сообщать о выгодных предложениях", priority=1),
        ]

    def filter_intentions(self) -> None:
        """Выбор приоритетных намерений на основе желаний."""
        if not self.desires:
            self.generate_desires()

        self.intentions = [
            Intention(description="Обновить данные из Steam", action="update_steam"),
            Intention(description="Загрузить топ скидок", action="fetch_deals"),
            Intention(description="Проверить цены отслеживаемых игр", action="check_watchlist"),
        ]

    async def act(self) -> None:
        """
        Действия агента: обновляет данные из реальных API.
        """
        try:
            # Временно отключаем автоматическую генерацию событий
            # чтобы избежать дублирования ключей в React
            
            # Загружаем скидки Steam (без генерации событий)
            steam_specials = await steam_service.get_specials(limit=15)
            if steam_specials:
                self.beliefs.last_steam_specials = steam_specials

            # Загружаем топ скидок с CheapShark (без генерации событий)
            top_deals = await cheapshark_service.get_top_deals(limit=10)
            if top_deals:
                self.beliefs.last_top_deals = top_deals

            # Обновляем цены для отслеживаемых игр
            await self._update_watchlist_prices()

            self.beliefs.last_update = datetime.now()

        except Exception as e:
            print(f"[BDIAgent] act error: {e}")

    async def _update_watchlist_prices(self) -> None:
        """Обновить цены игр в списке отслеживания."""
        print(f"[DEBUG] Starting price update for {len(self.beliefs.games)} games")
        for game_id, game in list(self.beliefs.games.items()):
            print(f"[DEBUG] Processing game: {game.title}, external_id: {game.external_id}, source: {game.source} (type: {type(game.source)})")
            if game.external_id and (str(game.source) == "steam" or game.source.value == "steam"):
                try:
                    print(f"[DEBUG] Fetching Steam details for {game.external_id}")
                    # Добавляем задержку между запросами к Steam
                    await asyncio.sleep(1)
                    
                    details = await steam_service.get_app_details(game.external_id)
                    print(f"[DEBUG] Got Steam details: {bool(details)}")
                    if details:
                        old_price = game.current_price
                        new_price = details.get("final_price")
                        print(f"[DEBUG] Price update: {old_price} -> {new_price}")
                        if new_price is not None:
                            # Steam возвращает цены в копейках
                            new_price_formatted = new_price / 100

                            if old_price is not None and new_price_formatted < old_price:
                                event = TrendEvent(
                                    id=self._generate_event_id(),
                                    game_id=game_id,
                                    type=TrendEventType.PRICE_DROP,
                                    title=f"📉 Цена на {game.title} снизилась!",
                                    description=f"Было: {old_price:.2f} {game.currency} → "
                                               f"Стало: {new_price_formatted:.2f} {game.currency}",
                                )
                                self.beliefs.events.append(event)

                            game.current_price = new_price_formatted
                            game.discount_percent = details.get("discount_percent")
                            if details.get("initial_price"):
                                game.original_price = details["initial_price"] / 100
                            
                            # Сохраняем полную информацию об игре для контекста AI
                            game._steam_details = details
                            print(f"[DEBUG] Updated game {game.title} with Steam details")
                            
                except Exception as e:
                    print(f"[BDIAgent] Error updating price for {game.title}: {e}")
            else:
                print(f"[DEBUG] Skipping game {game.title} - no external_id or not steam")
        print(f"[DEBUG] Price update completed")

    def _format_price_info(self, item: dict) -> str:
        """Форматирование информации о цене."""
        original = item.get("original_price")
        final = item.get("final_price")
        currency = item.get("currency", "RUB")

        if original and final:
            # Steam возвращает цены в копейках
            original_fmt = original / 100 if original > 1000 else original
            final_fmt = final / 100 if final > 1000 else final
            return f"Было: {original_fmt:.2f} {currency} → Сейчас: {final_fmt:.2f} {currency}"
        elif final:
            final_fmt = final / 100 if final > 1000 else final
            return f"Цена: {final_fmt:.2f} {currency}"
        return "Цена уточняется"

    # === Публичные методы API ===

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Запустить фоновый мониторинг (раз в минуту, чтобы не спамить API)."""
        if self._monitoring_task and not self._monitoring_task.done():
            return

        async def _loop() -> None:
            while True:
                self.filter_intentions()
                await self.act()
                await asyncio.sleep(interval_seconds)

        self._monitoring_task = asyncio.create_task(_loop())

    def get_watchlist(self) -> List[Game]:
        return list(self.beliefs.games.values())

    def apply_watchlist(self, games: List[Game]) -> List[Game]:
        self.update_beliefs_from_watchlist(games)
        # Принудительно обновляем данные для новых игр СРАЗУ
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._update_watchlist_prices())
        except Exception as e:
            print(f"[BDIAgent] Error scheduling price update: {e}")
        return self.get_watchlist()

    def get_recent_events(self, limit: int = 20) -> List[TrendEvent]:
        return self.beliefs.events[-limit:]

    async def search_games(self, query: str) -> List[dict]:
        """Поиск игр через Steam API."""
        return await steam_service.search_games(query, limit=10)

    async def get_game_details(self, appid: str) -> Optional[dict]:
        """Детали игры по Steam AppID."""
        return await steam_service.get_app_details(appid)

    async def get_top_deals(self) -> List[dict]:
        """Получить топ скидок с CheapShark."""
        return await cheapshark_service.get_top_deals(limit=15)

    async def get_steam_specials(self) -> List[dict]:
        """Получить текущие скидки Steam."""
        return await steam_service.get_specials(limit=20)

    # Epic Games Store методы
    async def get_epic_free_games(self) -> List[dict]:
        """Получить бесплатные игры в Epic Games Store."""
        return await epic_service.get_free_games()
    
    async def get_epic_deals(self) -> List[dict]:
        """Получить скидки в Epic Games Store."""
        return await epic_service.get_deals()

    # GOG методы
    async def get_gog_deals(self) -> List[dict]:
        """Получить скидки в GOG."""
        return await gog_service.get_deals()
    
    async def get_gog_free_games(self) -> List[dict]:
        """Получить бесплатные игры в GOG."""
        return await gog_service.get_free_games()
    
    async def get_gog_classic_games(self) -> List[dict]:
        """Получить классические игры в GOG."""
        return await gog_service.get_classic_games()
    
    async def search_gog_games(self, query: str) -> List[dict]:
        """Поиск игр в GOG."""
        return await gog_service.search_games(query)

    async def get_humble_bundles(self) -> List[Dict[str, Any]]:
        """Получить текущие бандлы Humble Bundle."""
        try:
            return await humble_service.get_current_bundles()
        except Exception as e:
            print(f"[DEBUG] Error getting Humble bundles: {e}")
            return []
    
    async def get_humble_monthly(self) -> List[Dict[str, Any]]:
        """Получить игры из Humble Choice."""
        try:
            return await humble_service.get_monthly_games()
        except Exception as e:
            print(f"[DEBUG] Error getting Humble Choice: {e}")
            return []
    
    async def get_humble_store_deals(self) -> List[Dict[str, Any]]:
        """Получить скидки в Humble Store."""
        try:
            return await humble_service.get_store_deals()
        except Exception as e:
            print(f"[DEBUG] Error getting Humble Store deals: {e}")
            return []
    
    async def search_humble_games(self, query: str) -> List[Dict[str, Any]]:
        """Поиск игр в Humble Bundle."""
        try:
            return await humble_service.search_games(query)
        except Exception as e:
            print(f"[DEBUG] Error searching Humble games: {e}")
            return []

    async def compare_prices(self, game_title: str) -> Optional[dict]:
        """Сравнить цены на игру на разных площадках."""
        games = await cheapshark_service.search_games(game_title, limit=1)
        if not games:
            return None
        game_id = games[0].get("game_id")
        if game_id:
            return await cheapshark_service.get_game_details(game_id)
        return None

    async def _gather_context(self, user_message: str) -> tuple[str, List[TrendEvent]]:
        """Собирает контекст для AI: актуальные данные + последние события."""
        user_lower = user_message.lower()
        context_parts: List[str] = []
        returned_events: List[TrendEvent] = []

        # Добавляем данные в зависимости от типа запроса
        # ВСЕГДА добавляем общие скидки при запросах о скидках или если контекст пустой
        if any(w in user_lower for w in ["скидк", "распродаж", "акци", "дешев", "предложен", "что интересного", "что посоветуешь"]) or not context_parts:
            print(f"[DEBUG] User asked about deals, getting specials...")
            # Скидки Steam
            try:
                specials = await steam_service.get_specials(limit=15)
                print(f"[DEBUG] Got {len(specials) if specials else 0} Steam specials")
                if specials:
                    context_parts.append("\n🔥 Текущие скидки в Steam:")
                    for s in specials[:10]:
                        final = s.get("final_price", 0)
                        original = s.get("original_price", 0)
                        final_fmt = final / 100 if final else 0
                        original_fmt = original / 100 if original else 0
                        discount = s.get("discount_percent", 0)
                        context_parts.append(f"- {s.get('name')}: {final_fmt:.0f} ₽ (было {original_fmt:.0f} ₽, скидка {discount}%)")
            except Exception as e:
                print(f"[DEBUG] Error getting Steam specials: {e}")

            # Топ скидок со всех площадок
            try:
                top_deals = await self.get_top_deals()
                print(f"[DEBUG] Got {len(top_deals) if top_deals else 0} top deals")
                if top_deals:
                    context_parts.append("\n💰 Лучшие скидки на всех площадках:")
                    for d in top_deals[:15]:
                        sale_price = d.get('sale_price', 0)
                        normal_price = d.get('normal_price', 0)
                        savings = d.get('savings_percent', 0)
                        store = d.get('store_name', 'Unknown')
                        title = d.get('title', 'Unknown Game')
                        print(f"[DEBUG] Deal: {title} - {store} - ${sale_price}")
                        context_parts.append(f"- {title}: ${sale_price:.2f} (было ${normal_price:.2f}, скидка {savings:.0f}%) в {store}")
            except Exception as e:
                print(f"[DEBUG] Error getting top deals: {e}")

        # Добавляем бесплатные игры при запросе о бесплатных играх
        if any(w in user_lower for w in ["бесплатн", "free", "бесплатные", "халява"]):
            print(f"[DEBUG] User asked about free games...")
            
            # Бесплатные игры в Steam (если есть)
            try:
                specials = await steam_service.get_specials(limit=20)
                free_games = [s for s in specials if s.get("final_price", 0) == 0]
                if free_games:
                    context_parts.append("\n🆓 Бесплатные игры в Steam:")
                    for game in free_games[:5]:
                        context_parts.append(f"- {game.get('name')}: {game.get('description', '')[:100]}...")
            except Exception as e:
                print(f"[DEBUG] Error getting Steam free games: {e}")

            # Почти бесплатные игры (до $1)
            try:
                top_deals = await self.get_top_deals()
                almost_free = [d for d in top_deals if float(d.get('sale_price', 0)) <= 1.0]
                if almost_free:
                    context_parts.append("\n🆓 Почти бесплатные игры (до $1):")
                    for game in almost_free[:8]:  # Показываем 8 игр
                        title = game.get('title', 'Unknown')
                        price = game.get('sale_price', 0)
                        store = game.get('store_name', 'Unknown')
                        context_parts.append(f"- {title}: ${price:.2f} в {store}")
            except Exception as e:
                print(f"[DEBUG] Error getting almost free games: {e}")

            # Бесплатные игры в Humble Bundle
            try:
                humble_bundles = await self.get_humble_bundles()
                if humble_bundles:
                    context_parts.append("\n🎁 Текущие бандлы Humble Bundle:")
                    for bundle in humble_bundles[:3]:
                        games_preview = ", ".join([g.get('title', 'Unknown') for g in bundle.get('games', [])[:3]])
                        context_parts.append(f"- {bundle.get('title')}: {games_preview}")
            except Exception as e:
                print(f"[DEBUG] Error getting Humble bundles: {e}")

        # Добавляем бандлы Humble Bundle при общих запросах
        if any(w in user_lower for w in ["бандл", "bundle", "что интересного", "что посоветуешь"]) or not context_parts:
            try:
                humble_bundles = await self.get_humble_bundles()
                if humble_bundles:
                    context_parts.append("\n🎁 Текущие бандлы Humble Bundle:")
                    for bundle in humble_bundles[:3]:
                        games_preview = ", ".join([g.get('title', 'Unknown') for g in bundle.get('games', [])[:3]])
                        context_parts.append(f"- {bundle.get('title')}: {games_preview}")
            except Exception as e:
                print(f"[DEBUG] Error getting Humble bundles: {e}")

            # Скидки в Humble Store
            try:
                humble_deals = await self.get_humble_store_deals()
                if humble_deals:
                    context_parts.append("\n🛒 Скидки в Humble Store:")
                    for game in humble_deals[:5]:
                        context_parts.append(f"- {game.get('title')}: ${game.get('discount_price', 0):.2f} (было ${game.get('original_price', 0):.2f}, скидка {game.get('discount_percent', 0)}%)")
            except Exception as e:
                print(f"[DEBUG] Error getting Humble Store deals: {e}")

        # Сравнение цен при прямом запросе
        if any(w in user_lower for w in ["сравн", "где купить", "дешевле", "лучше купить"]):
            print(f"[DEBUG] User asked for price comparison...")
            for phrase in ["сравнить цены на", "сравни цены на", "где купить", "где дешевле", "лучше купить"]:
                if phrase in user_lower:
                    game_name = user_message.lower().replace(phrase, "").strip()
                    break
            else:
                # Ищем название игры в сообщении
                words = user_message.split()
                for i, word in enumerate(words):
                    if word.lower() in ["где", "лучше", "дешевле", "купить"] and i + 1 < len(words):
                        game_name = " ".join(words[i+1:])
                        break
                else:
                    game_name = user_message.strip()
            
            if len(game_name) > 2:
                print(f"[DEBUG] Searching for: {game_name}")
                # Ищем игру в CheapShark
                try:
                    search_results = await cheapshark_service.search_games(game_name, limit=5)
                    if search_results:
                        context_parts.append(f"\n🔍 Найдены магазины для игры:")
                        for result in search_results[:3]:
                            title = result.get("title", "Unknown")
                            store = result.get("store_name", "Unknown")
                            price = result.get("sale_price", result.get("normal_price", 0))
                            if price:
                                context_parts.append(f"- {title}: ${price:.2f} в {store}")
                    else:
                        # Ищем в Humble Store
                        humble_results = await self.search_humble_games(game_name)
                        if humble_results:
                            context_parts.append(f"\n🔍 Найдены магазины для игры:")
                            for result in humble_results[:3]:
                                title = result.get("title", "Unknown")
                                price = result.get("price", 0)
                                store = result.get("store", "Humble Store")
                                if price > 0:
                                    context_parts.append(f"- {title}: ${price:.2f} в {store}")
                                else:
                                    context_parts.append(f"- {title}: Бесплатно в {store}")
                except Exception as e:
                    print(f"[DEBUG] Error searching for game: {e}")
                try:
                    comp = await self.compare_prices(game_name)
                    if comp and comp.get("deals"):
                        context_parts.append(f"\n🔍 Сравнение цен на {comp.get('title')}:")
                        for d in comp["deals"][:5]:
                            context_parts.append(f"- {d.get('store_name')}: ${d.get('price'):.2f} (-{d.get('savings_percent', 0):.0f}%)")
                        if comp.get("cheapest_price_ever"):
                            context_parts.append(f"📉 Исторический минимум: ${comp['cheapest_price_ever']:.2f}")
                except Exception as e:
                    print(f"[DEBUG] Error comparing prices: {e}")

        # Поиск игры (через Steam)
        if any(w in user_lower for w in ["найти", "поиск", "ищу"]):
            q = user_message.replace("найти", "").replace("поиск", "").replace("ищу", "").strip()
            if len(q) > 2:
                try:
                    results = await self.search_games(q)
                    if results:
                        context_parts.append(f"\n🔎 Результаты поиска '{q}':")
                        for g in results[:5]:
                            context_parts.append(f"- {g.get('name')}: {g.get('price_formatted', 'Бесплатно')}")
                except Exception as e:
                    print(f"[DEBUG] Error searching games: {e}")

        # Классические игры при запросах
        if any(w in user_lower for w in ["классик", "старые", "ретро", "old school", "ностальгия"]):
            try:
                classic_games = await self.get_gog_classic_games()
                if classic_games:
                    context_parts.append("\n🕹️ Классические игры в GOG:")
                    for game in classic_games[:5]:
                        price = f" - {game.get('price', 0):.2f} {game.get('currency', 'USD')}" if game.get('price', 0) > 0 else " - Бесплатно"
                        genres = f" [{', '.join(game.get('genres', [])[:2])}]" if game.get('genres') else ""
                        context_parts.append(f"- {game.get('title')}{price}{genres}")
            except Exception as e:
                print(f"[DEBUG] Error getting classic games: {e}")

        # Мониторинг (отслеживаемые игры)
        watchlist = self.get_watchlist()
        if watchlist:
            context_parts.append("\n📋 Твои отслеживаемые игры:")
            for g in watchlist:
                price = f"{g.current_price:.2f} {g.currency}" if g.current_price else "цена неизвестна"
                disc = f" (-{g.discount_percent}%)" if g.discount_percent else ""
                context_parts.append(f"- {g.title}: {price}{disc}")
                
                # Добавляем подробную информацию из Steam если есть
                if hasattr(g, '_steam_details') and g._steam_details:
                    details = g._steam_details
                    desc = details.get("short_description", "")
                    if desc and len(desc) > 50:
                        desc = desc[:200] + "..."
                    if desc:
                        context_parts.append(f"  📝 {desc}")
                    
                    genres = details.get("genres", [])
                    if genres:
                        genre_names = []
                        for genre in genres:
                            if isinstance(genre, dict):
                                genre_names.append(genre.get("description", ""))
                            elif isinstance(genre, str):
                                genre_names.append(genre)
                        if genre_names:
                            context_parts.append(f"  🎮 {', '.join(genre_names[:3])}")

        print(f"[DEBUG] Final context parts: {len(context_parts)} items")
        print(f"[DEBUG] Context preview: {context_parts[:3]}")
        print(f"[DEBUG] Full context: {' '.join(context_parts[:15])}")  # Показываем первые 15 элементов
        print(f"[DEBUG] Looking for free games context...")
        for i, part in enumerate(context_parts):
            if "бесплатн" in part.lower() or "free" in part.lower():
                print(f"[DEBUG] Found free games section at index {i}: {part}")
                break
            elif "почти бесплат" in part.lower():
                print(f"[DEBUG] Found almost free games section at index {i}: {part}")
                break  
        
        return "\n".join(context_parts) if context_parts else "Нет данных. Предложи пользователю добавить игры в мониторинг или задать вопрос о скидках.", returned_events

    async def _fallback_reply(self, user_message: str) -> tuple[str, List[TrendEvent]]:
        """Резервный ответ без AI (если Groq недоступен)."""
        context, events = await self._gather_context(user_message)
        reply = (
            "Вот актуальные данные:\n\n" + context
            if context and "Нет данных" not in context
            else "👋 Привет! Я игровой AI-агент. Спроси про скидки, поиск игр или сравнение цен. "
                 "(AI временно недоступен — показываю сырые данные.) 🎮"
        )
        return reply, events

    async def chat(self, messages: List[ChatMessage]) -> ChatResponse:
        """
        Умный чат с AI (Groq/Llama). Использует реальные данные как контекст.
        При недоступности AI — fallback на rule-based ответ.
        """
        user_message = next((m.content for m in reversed(messages) if m.role == "user"), "")
        if not user_message.strip():
            return ChatResponse(
                reply="Напиши что-нибудь — могу помочь со скидками, поиском игр и сравнением цен! 🎮",
                events=[],
            )

        context, returned_events = await self._gather_context(user_message)

        if groq_available():
            system_prompt = (
                "Ты — дружелюбный игровой AI-помощник Gaming AI Assistant. "
                "Отвечай кратко, по-русски, с эмодзи там, где уместно. "
                "Используй ТОЛЬКО данные из контекста ниже. Если данных нет — честно скажи. "
                "ВАЖНО: Показывай игры из ВСЕХ магазинов (Steam, Gamesplanet, GameBillet, Fanatical и др.). "
                "Обязательно указывай названия магазинов и цены для не-Steam игр. "
                "Структурируй ответ по магазинам для удобства чтения. "
                "При запросе бесплатных игр показывай 'почти бесплатные' игры (до $1) как хорошие предложения. "
                "Не выдумывай данные, которых нет в контексте."
                "Не выдумывай цены и названия игр.\n\n"
                "КОНТЕКСТ (актуальные данные):\n" + context
            )
            def _role(m: ChatMessage) -> str:
                r = m.role
                return r.value if hasattr(r, "value") else str(r)

            history = [
                {"role": _role(m), "content": m.content}
                for m in messages[-8:]
            ]
            ai_reply = await groq_chat(
                messages=history,
                system_prompt=system_prompt,
                max_tokens=800,
            )
            if ai_reply:
                return ChatResponse(reply=ai_reply.strip(), events=returned_events)

        reply, _ = await self._fallback_reply(user_message)
        return ChatResponse(reply=reply, events=returned_events)


# Глобальный экземпляр агента
agent = GamingBDIAgent()
