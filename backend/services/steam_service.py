"""
Steam Store API Service

Работа с публичным Steam Store API (не требует ключа для базовых запросов).
Документация: https://wiki.teamfortress.com/wiki/User:RJackson/StorefrontAPI
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

# Таймаут для запросов
TIMEOUT = 15.0

# Базовые URL
STEAM_STORE_API = "https://store.steampowered.com/api"
STEAM_SEARCH_SUGGEST = "https://store.steampowered.com/search/suggest"


class SteamService:
    """Сервис для работы со Steam Store API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=TIMEOUT)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_games(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Поиск игр по названию.
        Возвращает список с базовой информацией: appid, name.
        """
        client = await self._get_client()
        try:
            # Steam suggest API возвращает HTML, поэтому используем другой подход
            # Используем storefront API для поиска
            url = f"{STEAM_STORE_API}/storesearch/"
            params = {
                "term": query,
                "l": "russian",  # Локализация
                "cc": "RU",  # Регион для цен
            }
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = []
            items = data.get("items", [])[:limit]
            for item in items:
                results.append({
                    "appid": item.get("id"),
                    "name": item.get("name"),
                    "tiny_image": item.get("tiny_image"),
                    "price": item.get("price", {}).get("final") if item.get("price") else None,
                    "price_formatted": item.get("price", {}).get("final_formatted") if item.get("price") else "Бесплатно",
                })
            return results
        except Exception as e:
            print(f"[SteamService] search_games error: {e}")
            return []

    async def get_app_details(self, appid: int | str, cc: str = "RU") -> Optional[dict[str, Any]]:
        """
        Получить детальную информацию об игре по Steam AppID.
        
        Args:
            appid: Steam Application ID
            cc: Код страны для цен (RU, US, EU и т.д.)
        
        Returns:
            Словарь с информацией об игре или None, если не найдено.
        """
        client = await self._get_client()
        try:
            url = f"{STEAM_STORE_API}/appdetails"
            params = {
                "appids": str(appid),
                "cc": cc,
                "l": "russian",
            }
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            app_data = data.get(str(appid), {})
            if not app_data.get("success"):
                return None

            info = app_data.get("data", {})
            price_overview = info.get("price_overview", {})

            return {
                "appid": appid,
                "name": info.get("name"),
                "type": info.get("type"),  # game, dlc, demo, etc.
                "is_free": info.get("is_free", False),
                "short_description": info.get("short_description"),
                "header_image": info.get("header_image"),
                "developers": info.get("developers", []),
                "publishers": info.get("publishers", []),
                "genres": [g.get("description") for g in info.get("genres", [])],
                "categories": [c.get("description") for c in info.get("categories", [])],
                "release_date": info.get("release_date", {}).get("date"),
                "coming_soon": info.get("release_date", {}).get("coming_soon", False),
                "metacritic_score": info.get("metacritic", {}).get("score"),
                "recommendations": info.get("recommendations", {}).get("total"),
                # Ценовая информация
                "currency": price_overview.get("currency", "RUB"),
                "initial_price": price_overview.get("initial"),  # в копейках
                "final_price": price_overview.get("final"),  # в копейках
                "discount_percent": price_overview.get("discount_percent", 0),
                "final_formatted": price_overview.get("final_formatted"),
                "initial_formatted": price_overview.get("initial_formatted"),
            }
        except Exception as e:
            print(f"[SteamService] get_app_details error for {appid}: {e}")
            return None

    async def get_featured(self) -> list[dict[str, Any]]:
        """Получить список featured (рекомендуемых) игр."""
        client = await self._get_client()
        try:
            url = f"{STEAM_STORE_API}/featured"
            params = {"cc": "RU", "l": "russian"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("featured_win", [])[:15]:
                results.append({
                    "appid": item.get("id"),
                    "name": item.get("name"),
                    "discounted": item.get("discounted", False),
                    "discount_percent": item.get("discount_percent", 0),
                    "original_price": item.get("original_price"),  # в копейках
                    "final_price": item.get("final_price"),  # в копейках
                    "currency": item.get("currency", "RUB"),
                    "large_capsule_image": item.get("large_capsule_image"),
                    "header_image": item.get("header_image"),
                })
            return results
        except Exception as e:
            print(f"[SteamService] get_featured error: {e}")
            return []

    async def get_specials(self, limit: int = 20) -> list[dict[str, Any]]:
        """Получить список игр со скидками (specials)."""
        client = await self._get_client()
        try:
            url = f"{STEAM_STORE_API}/featuredcategories"
            params = {"cc": "RU", "l": "russian"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            specials = data.get("specials", {}).get("items", [])[:limit]
            results = []
            for item in specials:
                results.append({
                    "appid": item.get("id"),
                    "name": item.get("name"),
                    "discounted": item.get("discounted", True),
                    "discount_percent": item.get("discount_percent", 0),
                    "original_price": item.get("original_price"),
                    "final_price": item.get("final_price"),
                    "currency": item.get("currency", "RUB"),
                    "header_image": item.get("header_image"),
                })
            return results
        except Exception as e:
            print(f"[SteamService] get_specials error: {e}")
            return []


# Глобальный экземпляр сервиса
steam_service = SteamService()
