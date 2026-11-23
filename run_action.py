import asyncio
import logging
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, TARGET_CHAT_ID
from parser import get_all_giveaways, get_active_gamerpower_ids
import state

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def escape_html(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def run_once():
    if not BOT_TOKEN or not TARGET_CHAT_ID:
        logging.error("BOT_TOKEN или TARGET_CHAT_ID не заданы!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # 1. Очистка неактуальных раздач
    logging.info("Очистка неактуальных раздач...")
    active_gp_ids = await get_active_gamerpower_ids()
    removed = state.clean_expired(active_gp_ids)
    logging.info(f"Удалено неактуальных раздач: {removed}")

    # 2. Получение всех текущих раздач
    logging.info("Получение раздач...")
    giveaways = await get_all_giveaways()
    new_count = 0

    for item in giveaways:
        gid = item["id"]
        if state.is_giveaway_sent(gid):
            continue

        title = escape_html(item.get("title", ""))
        platforms = escape_html(item.get("platforms", ""))
        item_type = escape_html(item.get("type", ""))
        source = item.get("source", "GamerPower")
        worth = escape_html(item.get("worth", ""))
        end_date = escape_html(item.get("end_date", ""))
        url = item.get("url", "")
        image_url = item.get("image")

        text = (
            f"🎁 <b>{title}</b>\n\n"
            f"📌 <b>Тип:</b> {item_type}\n"
            f"💻 <b>Платформа:</b> {platforms}\n"
            f"💰 <b>Обычная цена:</b> <s>{worth}</s> <b>0₽ / Бесплатно</b>\n"
            f"⏳ <b>До:</b> {end_date}\n\n"
            f"👉 <a href='{url}'><b>Забрать бесплатно</b></a>"
        )

        try:
            if image_url:
                await bot.send_photo(chat_id=TARGET_CHAT_ID, photo=image_url, caption=text)
            else:
                await bot.send_message(chat_id=TARGET_CHAT_ID, text=text, disable_web_page_preview=False)

            state.mark_giveaway_sent(gid, item["title"], source)
            new_count += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            logging.error(f"Ошибка при отправке {gid}: {e}")

    await bot.session.close()
    logging.info(f"Завершено. Опубликовано новых раздач: {new_count}")

if __name__ == "__main__":
    asyncio.run(run_once())
