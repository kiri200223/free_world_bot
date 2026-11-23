import json
import os
from typing import Set

DATA_FILE = "giveaways.json"

def load_data() -> dict:
    """Загружает состояние раздач из JSON файла."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Ошибка чтения {DATA_FILE}: {e}")
    return {"giveaways": {}}

def save_data(data: dict):
    """Сохраняет состояние раздач в JSON файл."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_giveaway_sent(giveaway_id: str) -> bool:
    data = load_data()
    return giveaway_id in data.get("giveaways", {})

def mark_giveaway_sent(giveaway_id: str, title: str, source: str):
    data = load_data()
    if "giveaways" not in data:
        data["giveaways"] = {}
    data["giveaways"][giveaway_id] = {
        "title": title,
        "source": source
    }
    save_data(data)

def clean_expired(active_gp_ids: Set[str]):
    """
    Удаляет неактуальные раздачи:
    - Для GamerPower: удаляет те, которых больше нет в active_gp_ids
    """
    data = load_data()
    giveaways = data.get("giveaways", {})
    to_delete = []

    for gid, info in giveaways.items():
        if info.get("source") == "GamerPower" and gid not in active_gp_ids:
            to_delete.append(gid)

    for gid in to_delete:
        del giveaways[gid]

    save_data(data)
    return len(to_delete)
