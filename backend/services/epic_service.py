import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EpicService:
    """Epic Games Store API клиент для бесплатных игр и эксклюзивов."""
    
    def __init__(self):
        self.base_url = "https://store-site-backend-static.ak.epicgames.com"
        
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
            
            # Используем рабочий endpoint для бесплатных игр
            response = await client.get(
                f"{self.base_url}/freeGamesPromotions",
                params={
                    "locale": "ru-RU",
                    "country": "RU",
                    "allowCountries": "RU"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                catalog = data.get("data", {}).get("Catalog", {})
                search_store = catalog.get("searchStore", {})
                elements = search_store.get("elements", [])
                
                for game_data in elements:
                    # Проверяем промо-акции
                    promotions = game_data.get("promotions", {})
                    promotional_offers = promotions.get("promotionalOffers", [])
                    upcoming_promotional_offers = promotions.get("upcomingPromotionalOffers", [])
                    
                    # Игра бесплатна если есть активная или будущая промо-акция
                    is_free = False
                    start_date = None
                    end_date = None
                    
                    # Проверяем активные промо
                    for promo in promotional_offers:
                        for offer in promo.get("promotionalOffers", []):
                            if offer.get("discountSetting", {}).get("discountPercentage") == 100:
                                is_free = True
                                start_date = offer.get("startDate")
                                end_date = offer.get("endDate")
                                break
                    
                    # Проверяем будущие промо
                    if not is_free:
                        for promo in upcoming_promotional_offers:
                            for offer in promo.get("promotionalOffers", []):
                                if offer.get("discountSetting", {}).get("discountPercentage") == 100:
                                    is_free = True
                                    start_date = offer.get("startDate")
                                    end_date = offer.get("endDate")
                                    break
                    
                    if is_free:
                        game_info = {
                            "title": game_data.get("title", "Unknown Game"),
                            "description": game_data.get("description", "")[:200] + "...",
                            "url": f"https://store.epicgames.com/p/{game_data.get('productSlug', '')}",
                            "image": None,
                            "start_date": start_date,
                            "end_date": end_date
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
            
            # Используем общий catalog endpoint с фильтрацией по скидкам
            response = await client.get(
                f"{self.base_url}/catalog",
                params={
                    "locale": "ru-RU",
                    "country": "RU",
                    "allowCountries": "RU",
                    "count": limit * 2,  # Запрашиваем больше, потом отфильтруем
                    "sortBy": "effectiveDate",
                    "sortDir": "DESC"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                catalog = data.get("data", {}).get("Catalog", {})
                search_store = catalog.get("searchStore", {})
                elements = search_store.get("elements", [])
                
                for game_data in elements:
                    price_info = game_data.get("price", {})
                    total_price = price_info.get("totalPrice", {})
                    
                    if total_price.get("discountPrice") and total_price.get("originalPrice"):
                        original_price = float(total_price.get("originalPrice", 0))
                        discount_price = float(total_price.get("discountPrice", 0))
                        
                        if original_price > discount_price:
                            discount_percent = int((1 - discount_price / original_price) * 100)
                            
                            # Добавляем только игры со значительными скидками
                            if discount_percent >= 10:
                                game_info = {
                                    "title": game_data.get("title", "Unknown Game"),
                                    "description": game_data.get("description", "")[:150] + "...",
                                    "original_price": original_price,
                                    "discount_price": discount_price,
                                    "discount_percent": discount_percent,
                                    "currency": total_price.get("fmtPrice", {}).get("currencyCode", "USD"),
                                    "url": f"https://store.epicgames.com/p/{game_data.get('productSlug', '')}",
                                    "store": "Epic Games Store",
                                    "image": None
                                }
                                
                                # Находим обложку
                                for image in game_data.get("keyImages", []):
                                    if image.get("type") == "DieselStoreFrontWide":
                                        game_info["image"] = image.get("url")
                                        break
                                
                                games.append(game_info)
                                
                                if len(games) >= limit:
                                    break
                
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
