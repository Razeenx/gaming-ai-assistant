import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HumbleBundleService:
    """Humble Bundle API клиент для бандлов, скидок и бесплатных игр."""
    
    def __init__(self):
        self.base_url = "https://www.humblebundle.com"
        self.api_url = "https://www.humblebundle.com/api/v1"
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент."""
        return httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "X-Requested-By": "humblebundle"
            }
        )
    
    async def get_current_bundles(self) -> List[Dict[str, Any]]:
        """Получить текущие бандлы."""
        try:
            client = await self._get_client()
            
            # Используем более простой endpoint
            response = await client.get("https://www.humblebundle.com/api/v1/bundles")
            
            if response.status_code == 200:
                bundles_data = response.json()
                bundles = []
                
                for bundle in bundles_data:
                    # Берем только активные бандлы
                    if bundle.get("is_live", False) and bundle.get("is_visible", True):
                        bundle_info = {
                            "title": bundle.get("name", "Unknown Bundle"),
                            "description": bundle.get("description", "")[:200] + "...",
                            "url": f"https://www.humblebundle.com/bundle/{bundle.get('url_name', '')}",
                            "bundle_type": bundle.get("bundle_type", "bundle"),
                            "start_date": bundle.get("start_date"),
                            "end_date": bundle.get("end_date"),
                            "image": None,
                            "games": []
                        }
                        
                        # Получаем игры в бандле
                        products = bundle.get("products", [])
                        for product in products[:5]:  # Показываем первые 5 игр
                            game_info = {
                                "title": product.get("human_name", "Unknown Game"),
                                "description": product.get("description", "")[:100] + "...",
                                "steam_app_id": None
                            }
                            
                            # Ищем Steam AppID
                            for download in product.get("downloads", []):
                                if download.get("platform") == "steam":
                                    for download_option in download.get("download_struct", []):
                                        if download_option.get("url"):
                                            # Извлекаем AppID из URL Steam
                                            import re
                                            steam_match = re.search(r'store\.steampowered\.com/app/(\d+)', download_option.get("url", ""))
                                            if steam_match:
                                                game_info["steam_app_id"] = int(steam_match.group(1))
                                            break
                                    break
                            
                            bundle_info["games"].append(game_info)
                        
                        # Находим обложку бандла
                        for image in bundle.get("tile_images", []):
                            if image.get("type") == "tile":
                                bundle_info["image"] = image.get("url")
                                break
                        
                        bundles.append(bundle_info)
                
                return bundles
            else:
                logger.error(f"Humble Bundle API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Humble Bundle error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_monthly_games(self) -> List[Dict[str, Any]]:
        """Получить игры из Humble Choice (ежемесячная подписка)."""
        try:
            client = await self._get_client()
            
            # Получаем информацию о Humble Choice
            response = await client.get(f"{self.api_url}/subscriptions")
            
            if response.status_code == 200:
                subscriptions = response.json()
                monthly_games = []
                
                for sub in subscriptions:
                    if sub.get("is_active", False) and "choice" in sub.get("name", "").lower():
                        sub_info = {
                            "title": sub.get("name", "Humble Choice"),
                            "description": sub.get("description", "")[:200] + "...",
                            "url": "https://www.humblebundle.com/subscription",
                            "games": []
                        }
                        
                        # Получаем игры из подписки
                        products = sub.get("products", [])
                        for product in products[:8]:  # Показываем 8 игр
                            game_info = {
                                "title": product.get("human_name", "Unknown Game"),
                                "description": product.get("description", "")[:100] + "...",
                                "steam_app_id": None
                            }
                            
                            # Ищем Steam AppID
                            for download in product.get("downloads", []):
                                if download.get("platform") == "steam":
                                    for download_option in download.get("download_struct", []):
                                        if download_option.get("url"):
                                            import re
                                            steam_match = re.search(r'store\.steampowered\.com/app/(\d+)', download_option.get("url", ""))
                                            if steam_match:
                                                game_info["steam_app_id"] = int(steam_match.group(1))
                                            break
                                    break
                            
                            sub_info["games"].append(game_info)
                        
                        monthly_games.append(sub_info)
                        break
                
                return monthly_games
            else:
                logger.error(f"Humble Choice API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Humble Choice error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_store_deals(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Получить скидки в Humble Store."""
        try:
            client = await self._get_client()
            
            # Humble Store не имеет публичного API для скидок, но можно использовать поиск
            # Ищем популярные игры со скидками
            response = await client.get(
                f"{self.api_url}/search",
                params={
                    "filter": "all",
                    "sort": "discount",
                    "request": 1,
                    "page": 0,
                    "page_size": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                results = data.get("results", [])
                for game_data in results:
                    current_price = game_data.get("current_price", {})
                    original_price = game_data.get("full_price", {})
                    
                    if current_price.get("amount") and original_price.get("amount"):
                        current_amount = float(current_price.get("amount", 0))
                        original_amount = float(original_price.get("amount", 0))
                        
                        if current_amount < original_amount:
                            discount_percent = int((1 - current_amount / original_amount) * 100)
                            
                            if discount_percent >= 10:  # Только значительные скидки
                                game_info = {
                                    "title": game_data.get("human_name", "Unknown Game"),
                                    "description": game_data.get("description", "")[:150] + "...",
                                    "original_price": original_amount,
                                    "discount_price": current_amount,
                                    "discount_percent": discount_percent,
                                    "currency": current_price.get("currency", "USD"),
                                    "url": f"https://www.humblebundle.com/store/{game_data.get('machine_name', '')}",
                                    "store": "Humble Store",
                                    "image": None,
                                    "steam_app_id": game_data.get("steam_app_id")
                                }
                                
                                # Находим обложку
                                if game_data.get("capsule_image"):
                                    game_info["image"] = game_data.get("capsule_image")
                                
                                games.append(game_info)
                
                return games
            else:
                logger.error(f"Humble Store API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Humble Store error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def search_games(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск игр в Humble Store."""
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"{self.api_url}/search",
                params={
                    "search": query,
                    "filter": "all",
                    "request": 1,
                    "page": 0,
                    "page_size": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                results = data.get("results", [])
                for game_data in results:
                    current_price = game_data.get("current_price", {})
                    original_price = game_data.get("full_price", {})
                    
                    game_info = {
                        "title": game_data.get("human_name", "Unknown Game"),
                        "description": game_data.get("description", "")[:150] + "...",
                        "price": float(current_price.get("amount", 0)),
                        "original_price": float(original_price.get("amount", 0)),
                        "discount_percent": 0,
                        "currency": current_price.get("currency", "USD"),
                        "url": f"https://www.humblebundle.com/store/{game_data.get('machine_name', '')}",
                        "store": "Humble Store",
                        "image": None,
                        "steam_app_id": game_data.get("steam_app_id")
                    }
                    
                    # Вычисляем скидку если есть
                    if game_info["original_price"] > game_info["price"]:
                        game_info["discount_percent"] = int((1 - game_info["price"] / game_info["original_price"]) * 100)
                    
                    # Находим обложку
                    if game_data.get("capsule_image"):
                        game_info["image"] = game_data.get("capsule_image")
                    
                    games.append(game_info)
                
                return games
            else:
                logger.error(f"Humble search API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Humble search error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def close(self):
        """Закрыть соединения."""
        pass

# Глобальный экземпляр сервиса
humble_service = HumbleBundleService()
