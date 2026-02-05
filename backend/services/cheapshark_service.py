"""
CheapShark API Service

Бесплатный API для сравнения цен игр на разных площадках:
Steam, GOG, Humble Bundle, Epic, GreenManGaming и др.

Документация: https://apidocs.cheapshark.com/
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

TIMEOUT = 15.0
BASE_URL = "https://www.cheapshark.com/api/1.0"

# Популярные магазины (storeID -> название)
STORES = {
    "1": "Steam",
    "2": "GamersGate",
    "3": "GreenManGaming",
    "7": "GOG",
    "8": "Origin",
    "11": "Humble Store",
    "13": "Uplay",
    "15": "Fanatical",
    "21": "WinGameStore",
    "23": "GameBillet",
    "24": "Voidu",
    "25": "Epic Games Store",
    "27": "Gamesplanet",
    "28": "Gamesload",
    "29": "2Game",
    "30": "IndieGala",
    "31": "Blizzard Shop",
    "33": "DLGamer",
    "34": "Noctre",
    "35": "Dreamgame",
}


class CheapSharkService:
    """Сервис для работы с CheapShark API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._stores_cache: dict[str, dict] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=TIMEOUT)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_stores(self) -> list[dict[str, Any]]:
        """Получить список поддерживаемых магазинов."""
        if self._stores_cache is not None:
            return list(self._stores_cache.values())

        client = await self._get_client()
        try:
            resp = await client.get(f"{BASE_URL}/stores")
            resp.raise_for_status()
            stores = resp.json()
            self._stores_cache = {s["storeID"]: s for s in stores}
            return stores
        except Exception as e:
            print(f"[CheapSharkService] get_stores error: {e}")
            return []

    def _get_store_name(self, store_id: str) -> str:
        """Получить название магазина по ID."""
        return STORES.get(store_id, f"Store #{store_id}")

    async def search_games(self, title: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Поиск игр по названию.
        Возвращает список игр с информацией о лучшей цене.
        """
        client = await self._get_client()
        try:
            params = {"title": title, "limit": limit}
            resp = await client.get(f"{BASE_URL}/games", params=params)
            resp.raise_for_status()
            games = resp.json()

            results = []
            for game in games:
                results.append({
                    "game_id": game.get("gameID"),
                    "steam_appid": game.get("steamAppID"),
                    "title": game.get("external"),  # Название
                    "cheapest_price": float(game.get("cheapest", 0)),
                    "cheapest_deal_id": game.get("cheapestDealID"),
                    "thumb": game.get("thumb"),
                })
            return results
        except Exception as e:
            print(f"[CheapSharkService] search_games error: {e}")
            return []

    async def get_game_details(self, game_id: str) -> Optional[dict[str, Any]]:
        """
        Получить детальную информацию об игре и все текущие предложения.
        """
        client = await self._get_client()
        try:
            params = {"id": game_id}
            resp = await client.get(f"{BASE_URL}/games", params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return None

            info = data.get("info", {})
            deals = data.get("deals", [])

            # Обогащаем deals названиями магазинов
            enriched_deals = []
            for deal in deals:
                enriched_deals.append({
                    "store_id": deal.get("storeID"),
                    "store_name": self._get_store_name(deal.get("storeID", "")),
                    "deal_id": deal.get("dealID"),
                    "price": float(deal.get("price", 0)),
                    "retail_price": float(deal.get("retailPrice", 0)),
                    "savings_percent": float(deal.get("savings", 0)),
                })

            return {
                "game_id": game_id,
                "title": info.get("title"),
                "steam_appid": info.get("steamAppID"),
                "thumb": info.get("thumb"),
                "cheapest_price_ever": float(info.get("cheapestPriceEver", {}).get("price", 0)),
                "cheapest_price_ever_date": info.get("cheapestPriceEver", {}).get("date"),
                "deals": enriched_deals,
            }
        except Exception as e:
            print(f"[CheapSharkService] get_game_details error: {e}")
            return None

    async def get_deals(
        self,
        store_id: Optional[str] = None,
        upper_price: Optional[float] = None,
        lower_price: Optional[float] = None,
        min_metacritic: Optional[int] = None,
        min_steam_rating: Optional[int] = None,
        on_sale: bool = True,
        sort_by: str = "Deal Rating",  # Deal Rating, Title, Savings, Price, Metacritic, Reviews, Release, Store, recent
        desc: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Получить список текущих скидок/предложений.
        
        Args:
            store_id: ID магазина (1=Steam, 7=GOG, 25=Epic и т.д.)
            upper_price: Максимальная цена (USD)
            lower_price: Минимальная цена (USD)
            min_metacritic: Минимальный рейтинг Metacritic
            min_steam_rating: Минимальный рейтинг Steam (%)
            on_sale: Только товары со скидкой
            sort_by: Сортировка
            desc: Сортировка по убыванию
            limit: Количество результатов
        """
        client = await self._get_client()
        try:
            params: dict[str, Any] = {
                "pageSize": limit,
                "sortBy": sort_by,
                "desc": 1 if desc else 0,
            }
            if store_id:
                params["storeID"] = store_id
            if upper_price is not None:
                params["upperPrice"] = upper_price
            if lower_price is not None:
                params["lowerPrice"] = lower_price
            if min_metacritic:
                params["metacritic"] = min_metacritic
            if min_steam_rating:
                params["steamRating"] = min_steam_rating
            if on_sale:
                params["onSale"] = 1

            resp = await client.get(f"{BASE_URL}/deals", params=params)
            resp.raise_for_status()
            deals = resp.json()

            results = []
            for deal in deals:
                results.append({
                    "deal_id": deal.get("dealID"),
                    "title": deal.get("title"),
                    "store_id": deal.get("storeID"),
                    "store_name": self._get_store_name(deal.get("storeID", "")),
                    "game_id": deal.get("gameID"),
                    "sale_price": float(deal.get("salePrice", 0)),
                    "normal_price": float(deal.get("normalPrice", 0)),
                    "savings_percent": float(deal.get("savings", 0)),
                    "metacritic_score": deal.get("metacriticScore"),
                    "steam_rating_percent": deal.get("steamRatingPercent"),
                    "steam_rating_count": deal.get("steamRatingCount"),
                    "steam_appid": deal.get("steamAppID"),
                    "release_date": deal.get("releaseDate"),
                    "thumb": deal.get("thumb"),
                    "is_on_sale": deal.get("isOnSale") == "1",
                    "deal_rating": float(deal.get("dealRating", 0)),
                })
            return results
        except Exception as e:
            print(f"[CheapSharkService] get_deals error: {e}")
            return []

    async def get_top_deals(self, limit: int = 15) -> list[dict[str, Any]]:
        """Получить топ скидок с высоким рейтингом."""
        return await self.get_deals(
            on_sale=True,
            sort_by="Deal Rating",
            desc=True,
            limit=limit,
        )

    async def get_steam_deals(self, limit: int = 15) -> list[dict[str, Any]]:
        """Получить скидки только в Steam."""
        return await self.get_deals(
            store_id="1",  # Steam
            on_sale=True,
            sort_by="Savings",
            desc=True,
            limit=limit,
        )

    async def get_free_games(self, limit: int = 10) -> list[dict[str, Any]]:
        """Получить бесплатные игры (цена = 0)."""
        return await self.get_deals(
            upper_price=0,
            lower_price=0,
            on_sale=False,
            limit=limit,
        )

    def generate_deal_link(self, deal_id: str) -> str:
        """Сгенерировать ссылку на страницу покупки."""
        return f"https://www.cheapshark.com/redirect?dealID={deal_id}"


# Глобальный экземпляр сервиса
cheapshark_service = CheapSharkService()
