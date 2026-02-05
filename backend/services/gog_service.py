import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GOGService:
    """GOG.com API клиент для игр без DRM и классических игр."""
    
    def __init__(self):
        self.base_url = "https://api.gog.com"
        self.store_url = "https://embed.gog.com"
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент."""
        return httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def get_deals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить игры со скидками в GOG."""
        try:
            client = await self._get_client()
            
            # Используем рабочий endpoint GOG
            response = await client.get(
                f"{self.store_url}/products/ajax/filter",
                params={
                    "sort": "discount:desc",
                    "limit": limit,
                    "page": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                products = data.get("products", [])
                
                for product in products:
                    price = product.get("price", {})
                    
                    if price.get("discount") and price.get("discount") > 0:
                        game_info = {
                            "title": product.get("title"),
                            "slug": product.get("slug"),
                            "description": product.get("description", "")[:150] + "...",
                            "original_price": price.get("baseAmount", 0),
                            "discount_price": price.get("finalAmount", 0),
                            "discount_percent": price.get("discount", 0),
                            "currency": price.get("currency", "USD"),
                            "url": f"https://www.gog.com/game/{product.get('slug')}",
                            "store": "GOG",
                            "image": None
                        }
                        
                        # Находим обложку
                        if product.get("images"):
                            for image in product["images"]:
                                if image.get("type") == "productCard":
                                    game_info["image"] = image.get("url")
                                    break
                        
                        # Добавляем жанры если есть
                        genres = []
                        if product.get("genres"):
                            genres = [g.get("name", "") for g in product["genres"][:3]]
                        game_info["genres"] = genres
                        
                        games.append(game_info)
                
                return games
            else:
                logger.error(f"GOG deals API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"GOG deals error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_free_games(self) -> List[Dict[str, Any]]:
        """Получить бесплатные игры в GOG."""
        try:
            client = await self._get_client()
            
            # Используем рабочий endpoint для бесплатных игр
            response = await client.get(
                f"{self.store_url}/products/ajax/filter",
                params={
                    "price": "free",
                    "sort": "title:asc",
                    "limit": 10,
                    "page": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                products = data.get("products", [])
                
                for product in products:
                    game_info = {
                        "title": product.get("title"),
                        "slug": product.get("slug"),
                        "description": product.get("description", "")[:200] + "...",
                        "url": f"https://www.gog.com/game/{product.get('slug')}",
                        "store": "GOG",
                        "image": None
                    }
                    
                    # Находим обложку
                    if product.get("images"):
                        for image in product["images"]:
                            if image.get("type") == "productCard":
                                game_info["image"] = image.get("url")
                                break
                    
                    # Добавляем жанры
                    genres = []
                    if product.get("genres"):
                        genres = [g.get("name", "") for g in product["genres"][:3]]
                    game_info["genres"] = genres
                    
                    games.append(game_info)
                
                return games
            else:
                logger.error(f"GOG free games API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"GOG free games error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def search_games(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск игр в GOG."""
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"{self.store_url}/products/ajax/filter",
                params={
                    "search": query,
                    "limit": limit,
                    "page": 1,
                    "sort": "popularity:desc"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                products = data.get("products", [])
                
                for product in products:
                    price = product.get("price", {})
                    
                    game_info = {
                        "title": product.get("title"),
                        "slug": product.get("slug"),
                        "description": product.get("description", "")[:150] + "...",
                        "price": price.get("finalAmount", 0),
                        "original_price": price.get("baseAmount", 0),
                        "discount_percent": price.get("discount", 0),
                        "currency": price.get("currency", "USD"),
                        "url": f"https://www.gog.com/game/{product.get('slug')}",
                        "store": "GOG",
                        "is_free": price.get("finalAmount", 0) == 0,
                        "image": None
                    }
                    
                    # Находим обложку
                    if product.get("images"):
                        for image in product["images"]:
                            if image.get("type") == "productCard":
                                game_info["image"] = image.get("url")
                                break
                    
                    # Добавляем жанры
                    genres = []
                    if product.get("genres"):
                        genres = [g.get("name", "") for g in product["genres"][:3]]
                    game_info["genres"] = genres
                    
                    games.append(game_info)
                
                return games
            else:
                logger.error(f"GOG search API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"GOG search error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_classic_games(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Получить классические игры."""
        try:
            client = await self._get_client()
            
            # Ищем классические игры
            response = await client.get(
                f"{self.store_url}/products/ajax/filter",
                params={
                    "genre": "classic",
                    "limit": limit,
                    "page": 1,
                    "sort": "popularity:desc"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                products = data.get("products", [])
                
                for product in products:
                    price = product.get("price", {})
                    
                    game_info = {
                        "title": product.get("title"),
                        "slug": product.get("slug"),
                        "description": product.get("description", "")[:150] + "...",
                        "price": price.get("finalAmount", 0),
                        "original_price": price.get("baseAmount", 0),
                        "discount_percent": price.get("discount", 0),
                        "currency": price.get("currency", "USD"),
                        "url": f"https://www.gog.com/game/{product.get('slug')}",
                        "store": "GOG",
                        "release_date": product.get("releaseDate"),
                        "image": None
                    }
                    
                    # Находим обложку
                    if product.get("images"):
                        for image in product["images"]:
                            if image.get("type") == "productCard":
                                game_info["image"] = image.get("url")
                                break
                    
                    # Добавляем жанры
                    genres = []
                    if product.get("genres"):
                        genres = [g.get("name", "") for g in product["genres"][:3]]
                    game_info["genres"] = genres
                    
                    games.append(game_info)
                
                return games
            else:
                logger.error(f"GOG classic games API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"GOG classic games error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def close(self):
        """Закрыть соединения."""
        pass

# Глобальный экземпляр сервиса
gog_service = GOGService()
