import httpx
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EpicService:
    """Epic Games Store API клиент для бесплатных игр и эксклюзивов."""
    
    def __init__(self):
        self.base_url = "https://store-content.ak.epicgames.com"
        self.graphql_url = "https://graphql.epicgames.com/graphql"
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент."""
        return httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def get_free_games(self) -> List[Dict[str, Any]]:
        """Получить текущие бесплатные игры."""
        try:
            client = await self._get_client()
            
            # Используем публичный API Epic Games Store
            response = await client.get(
                "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
                params={
                    "locale": "ru-RU",
                    "country": "RU",
                    "allowCountries": "RU"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                catalog_data = data.get("data", {}).get("Catalog", {})
                if not catalog_data:
                    return games
                    
                search_store = catalog_data.get("searchStore", {})
                elements = search_store.get("elements", [])
                
                for game_data in elements:
                    # Проверяем, есть ли активная промо-акция
                    promotions = game_data.get("promotions", {})
                    promotional_offers = promotions.get("promotionalOffers", [])
                    
                    if promotional_offers or game_data.get("price", {}).get("totalPrice", {}).get("fmtPrice", {}).get("discountPrice") == "0":
                        game_info = {
                            "title": game_data.get("title", "Unknown Game"),
                            "description": game_data.get("description", "")[:200] + "...",
                            "url": f"https://store.epicgames.com/p/{game_data.get('productSlug', '')}",
                            "image": None
                        }
                        
                        # Находим обложку
                        for image in game_data.get("keyImages", []):
                            if image.get("type") == "DieselStoreFrontWide":
                                game_info["image"] = image.get("url")
                                break
                        
                        games.append(game_info)
                
                return games
            else:
                logger.error(f"Epic API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Epic free games error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_deals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить игры со скидками в Epic Games Store."""
        try:
            client = await self._get_client()
            
            # Используем публичный API для игр со скидками
            response = await client.get(
                "https://store-site-backend-static.ak.epicgames.com/catalog",
                params={
                    "locale": "ru-RU",
                    "country": "RU",
                    "allowCountries": "RU",
                    "sortBy": "discountPercentage",
                    "sortDir": "DESC",
                    "count": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                for game_data in data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []):
                    price_info = game_data.get("price", {})
                    total_price = price_info.get("totalPrice", {})
                    
                    if total_price.get("discountPrice") and total_price.get("originalPrice"):
                        original_price = float(total_price.get("originalPrice", 0))
                        discount_price = float(total_price.get("discountPrice", 0))
                        
                        if original_price > discount_price:
                            discount_percent = int((1 - discount_price / original_price) * 100)
                            
                            game_info = {
                                "title": game_data.get("title"),
                                "description": game_data.get("description", "")[:150] + "...",
                                "original_price": original_price,
                                "discount_price": discount_price,
                                "discount_percent": discount_percent,
                                "currency": total_price.get("fmtPrice", {}).get("currencyCode", "USD"),
                                "url": f"https://store.epicgames.com/p/{game_data.get('productSlug')}",
                                "store": "Epic Games Store"
                            }
                            
                            # Находим обложку
                            for image in game_data.get("keyImages", []):
                                if image.get("type") == "DieselStoreFrontWide":
                                    game_info["image"] = image.get("url")
                                    break
                            
                            games.append(game_info)
                
                return games
            else:
                logger.error(f"Epic deals API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Epic deals error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def close(self):
        """Закрыть соединения."""
        pass

# Глобальный экземпляр сервиса
epic_service = EpicService()
