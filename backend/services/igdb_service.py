import httpx
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class IGDBService:
    """IGDB API клиент для получения информации об играх, рейтингах и датах выхода."""
    
    def __init__(self):
        self.client_id = os.getenv("IGDB_CLIENT_ID")
        self.access_token = os.getenv("IGDB_ACCESS_TOKEN")
        self.base_url = "https://api.igdb.com/v4"
        self._token_expires_at = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент с актуальными токенами."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            },
            timeout=30.0
        )
    
    async def _ensure_valid_token(self) -> bool:
        """Проверить и обновить токен если нужно."""
        if not self.client_id or not self.access_token:
            logger.warning("IGDB credentials not configured")
            return False
        return True
    
    async def search_games(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск игр по названию."""
        if not await self._ensure_valid_token():
            return []
            
        try:
            async client = await self._get_client()
            response = await client.post(
                "/games",
                data=f"""
                fields name, summary, rating, rating_count, first_release_date, 
                      platforms.name, genres.name, cover.url, involved_companies.company.name,
                      websites.url, similar_games.name, total_rating, total_rating_count;
                search "{query}";
                limit {limit};
                where rating > 0;
                sort rating desc;
                """
            )
            
            if response.status_code == 200:
                games = response.json()
                return self._format_games(games)
            else:
                logger.error(f"IGDB search error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"IGDB search error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_game_details(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Получить подробную информацию об игре."""
        if not await self._ensure_valid_token():
            return None
            
        try:
            async client = await self._get_client()
            response = await client.post(
                "/games",
                data=f"""
                fields name, summary, rating, rating_count, total_rating, total_rating_count,
                      first_release_date, platforms.name, genres.name, cover.url, screenshots.url,
                      involved_companies.company.name, websites.url, similar_games.name,
                      storyline, dlcs.name, expansions.name, themes.name, age_ratings.rating,
                      game_modes.name, player_perspectives.name, multiplayer_modes;
                where id = {game_id};
                """
            )
            
            if response.status_code == 200:
                games = response.json()
                if games:
                    return self._format_game_details(games[0])
            return None
                
        except Exception as e:
            logger.error(f"IGDB details error: {e}")
            return None
        finally:
            await client.aclose()
    
    async def get_popular_games(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить популярные игры с высокими рейтингами."""
        if not await self._ensure_valid_token():
            return []
            
        try:
            async client = await self._get_client()
            response = await client.post(
                "/games",
                data=f"""
                fields name, summary, rating, rating_count, first_release_date, 
                      platforms.name, genres.name, cover.url, total_rating;
                where rating > 80 & rating_count > 100;
                sort rating desc;
                limit {limit};
                """
            )
            
            if response.status_code == 200:
                games = response.json()
                return self._format_games(games)
            return []
                
        except Exception as e:
            logger.error(f"IGDB popular games error: {e}")
            return []
        finally:
            await client.aclose()
    
    async def get_upcoming_games(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Получить ожидаемые игры."""
        if not await self._ensure_valid_token():
            return []
            
        try:
            current_timestamp = int(datetime.now().timestamp())
            async client = await self._get_client()
            response = await client.post(
                "/games",
                data=f"""
                fields name, summary, rating, rating_count, first_release_date, 
                      platforms.name, genres.name, cover.url, hypes;
                where first_release_date > {current_timestamp} & hypes > 10;
                sort hypes desc;
                limit {limit};
                """
            )
            
            if response.status_code == 200:
                games = response.json()
                return self._format_games(games)
            return []
                
        except Exception as e:
            logger.error(f"IGDB upcoming games error: {e}")
            return []
        finally:
            await client.aclose()
    
    def _format_games(self, games: List[Dict]) -> List[Dict[str, Any]]:
        """Форматировать список игр."""
        formatted = []
        for game in games:
            formatted.append(self._format_game_details(game))
        return [g for g in formatted if g]
    
    def _format_game_details(self, game: Dict) -> Optional[Dict[str, Any]]:
        """Форматировать детали игры."""
        if not game:
            return None
            
        # Конвертация timestamp в дату
        release_date = None
        if game.get("first_release_date"):
            release_date = datetime.fromtimestamp(game["first_release_date"]).strftime("%Y-%m-%d")
        
        # Платформы
        platforms = []
        if game.get("platforms"):
            platforms = [p.get("name") for p in game["platforms"] if p.get("name")]
        
        # Жанры
        genres = []
        if game.get("genres"):
            genres = [g.get("name") for g in game["genres"] if g.get("name")]
        
        # Обложка
        cover_url = None
        if game.get("cover") and game["cover"].get("url"):
            cover_url = game["cover"]["url"].replace("t_thumb", "t_cover_big")
        
        # Разработчики/издатели
        companies = []
        if game.get("involved_companies"):
            companies = [c.get("company", {}).get("name") for c in game["involved_companies"] 
                        if c.get("company", {}).get("name")]
        
        return {
            "id": game.get("id"),
            "name": game.get("name"),
            "summary": game.get("summary"),
            "storyline": game.get("storyline"),
            "rating": game.get("rating"),
            "rating_count": game.get("rating_count"),
            "total_rating": game.get("total_rating"),
            "total_rating_count": game.get("total_rating_count"),
            "release_date": release_date,
            "platforms": platforms,
            "genres": genres,
            "cover_url": cover_url,
            "companies": companies,
            "hypes": game.get("hypes"),
            "websites": [w.get("url") for w in game.get("websites", []) if w.get("url")]
        }
    
    async def close(self):
        """Закрыть соединения."""
        pass

# Глобальный экземпляр сервиса
igdb_service = IGDBService()
