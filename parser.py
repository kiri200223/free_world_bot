import aiohttp
import asyncio
import feedparser
from typing import List, Dict, Set

async def fetch_gamerpower_games() -> List[Dict]:
    """
    Получает активные раздачи игр со всех платформ (PC, Steam, Epic, GOG, PS, Xbox)
    через бесплатный GamerPower API.
    """
    giveaways = []
    url = "https://www.gamerpower.com/api/giveaways"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        giveaways.append({
                            "id": f"gp_{item.get('id')}",
                            "raw_id": item.get('id'),
                            "title": item.get("title", "Без названия"),
                            "description": item.get("description", ""),
                            "url": item.get("open_giveaway_url") or item.get("gamerpower_url"),
                            "platforms": item.get("platforms", "Любая"),
                            "type": "Игра",
                            "source": "GamerPower",
                            "worth": item.get("worth", "Бесплатно"),
                            "end_date": item.get("end_date", "Не указано"),
                            "image": item.get("image")
                        })
    except Exception as e:
        print(f"[!] Ошибка загрузки GamerPower: {e}")

    return giveaways

def _parse_rss_sync(feed_url: str, source_name: str, item_type: str) -> List[Dict]:
    """Синхронный парсер RSS через feedparser."""
    giveaways = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:15]:
            entry_id = entry.get("id") or entry.get("link")
            giveaways.append({
                "id": f"rss_{entry_id}",
                "raw_id": entry_id,
                "title": entry.get("title", "Без названия"),
                "description": entry.get("summary", "")[:200] if entry.get("summary") else "",
                "url": entry.get("link", ""),
                "platforms": source_name,
                "type": item_type,
                "source": source_name,
                "worth": "Бесплатно",
                "end_date": "Смотрите на сайте",
                "image": None
            })
    except Exception as e:
        print(f"[!] Ошибка парсинга RSS {feed_url}: {e}")
    return giveaways

async def fetch_software_rss() -> List[Dict]:
    """Сбор раздач программ/софта из RSS-лент."""
    loop = asyncio.get_running_loop()
    
    tasks = [
        loop.run_in_executor(None, _parse_rss_sync, "https://www.comss.one/rss.php", "Comss / ПК", "Программа"),
        loop.run_in_executor(None, _parse_rss_sync, "https://www.reddit.com/r/FreeGameFindings/.rss", "Reddit / Скидки", "Игра/DLC"),
    ]
    
    results = await asyncio.gather(*tasks)
    all_rss_items = []
    for res in results:
        all_rss_items.extend(res)
    return all_rss_items

async def get_all_giveaways() -> List[Dict]:
    """Объединяет все актуальные активные раздачи."""
    games, software = await asyncio.gather(
        fetch_gamerpower_games(),
        fetch_software_rss()
    )
    return games + software

async def get_active_gamerpower_ids() -> Set[str]:
    """
    Возвращает множество ID всех СЕЙЧАС активных раздач на GamerPower.
    Если раздачи нет в этом списке — она закончилась.
    """
    games = await fetch_gamerpower_games()
    return {g["id"] for g in games}
