import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import handlers
from .config import get_config
from .database import DatabaseManager


logger = logging.getLogger(__name__)


async def run_bot(
    db_manager: DatabaseManager,
    shutdown_event: asyncio.Event
) -> None:
    config = get_config()
    
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    handlers.register_handlers(dp, db_manager, config)
    
    logger.info("Бот запущен и готов к работе")
    
    polling_task = asyncio.create_task(dp.start_polling(bot))
    shutdown_task = asyncio.create_task(shutdown_event.wait())
    
    done, pending = await asyncio.wait(
        {polling_task, shutdown_task},
        return_when=asyncio.FIRST_COMPLETED
    )
    
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    await bot.session.close()
    logger.info("Бот корректно завершил работу")
