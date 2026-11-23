import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, TARGET_CHAT_ID, SEND_HOUR, SEND_MINUTE
from database import (
    init_db, 
    is_giveaway_sent, 
    mark_giveaway_sent, 
    get_all_stored_giveaways, 
    remove_expired_giveaway,
    clean_old_rss_giveaways
)
from parser import get_all_giveaways, get_active_gamerpower_ids

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

def escape_html(text: str) -> str:
    """Экранирование спецсимволов HTML."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def clean_expired_giveaways():
    """
    Проверяет базу данных и удаляет неактуальные раздачи:
    1. Для GamerPower (игры): сверяет с текущим активным списком API. Если раздачи нет — удаляет.
    2. Для RSS (софт): удаляет раздачи старше 7 дней.
    """
    logging.info("🧹 Начинаем очистку неактуальных раздач из базы данных...")
    
    # 1. Сверка GamerPower
    active_gp_ids = await get_active_gamerpower_ids()
    stored_items = await get_all_stored_giveaways()
    
    removed_count = 0
    for giveaway_id, source in stored_items:
        if source == "GamerPower" and giveaway_id not in active_gp_ids:
            await remove_expired_giveaway(giveaway_id)
            removed_count += 1
            logging.info(f"Удалена закончившаяся раздача: {giveaway_id}")
            
    # 2. Очистка старых записей из RSS (> 7 дней)
    removed_rss = await clean_old_rss_giveaways(days=7)
    
    total_removed = removed_count + removed_rss
    logging.info(f"Очистка завершена. Удалено неактуальных записей: {total_removed} (Игр: {removed_count}, RSS: {removed_rss})")

async def send_daily_giveaways():
    """Основная функция: проверяет актуальность, удаляет просроченные и отправляет новые."""
    if not TARGET_CHAT_ID:
        logging.warning("TARGET_CHAT_ID не настроен в .env! Рассылка отменена.")
        return

    # Сначала удаляем неактуал из базы данных
    await clean_expired_giveaways()

    logging.info("Поиск новых раздач...")
    giveaways = await get_all_giveaways()
    new_count = 0

    for item in giveaways:
        giveaway_id = item["id"]
        
        # Проверяем в БД: отправляли ли уже?
        if await is_giveaway_sent(giveaway_id):
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
            
            await mark_giveaway_sent(giveaway_id, item["title"], source)
            new_count += 1
            await asyncio.sleep(1.5)  # Защита от спам-лимитов Telegram
        except Exception as e:
            logging.error(f"Ошибка при отправке раздачи {giveaway_id}: {e}")

    logging.info(f"Проверка завершена. Отправлено новых раздач: {new_count}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>Привет!</b> Я бот для мониторинга бесплатных раздач игр и программ.\n\n"
        f"Ваш Telegram Chat ID: <code>{message.chat.id}</code>\n\n"
        "Команды:\n"
        "• /check — проверить и прислать свежие раздачи прямо сейчас.\n"
        "• /clean — принудительно очистить базу от неактуальных раздач."
    )

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    """Принудительная ручная проверка и рассылка."""
    await message.answer("🔍 Очищаю неактуал и ищу свежие раздачи...")
    await send_daily_giveaways()
    await message.answer("✅ Готово!")

@dp.message(Command("clean"))
async def cmd_clean(message: types.Message):
    """Ручной запуск очистки базы данных от протухших раздач."""
    await message.answer("🧹 Очистка неактуальных раздач из базы...")
    await clean_expired_giveaways()
    await message.answer("✅ База данных успешно очищена от неактуальных раздач!")

async def main():
    if not BOT_TOKEN:
        print("\n[!] ОШИБКА: Пожалуйста, укажите BOT_TOKEN в файле .env!\n")
        return

    await init_db()

    # Запуск планировщика раз в сутки
    scheduler.add_job(
        send_daily_giveaways,
        trigger="cron",
        hour=SEND_HOUR,
        minute=SEND_MINUTE
    )
    scheduler.start()
    logging.info(f"Планировщик запущен. Ежедневный сбор и очистка запланированы на {SEND_HOUR:02d}:{SEND_MINUTE:02d}")

    logging.info("Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
