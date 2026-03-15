import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from .config import Config
from .database import DatabaseError, DatabaseManager


logger = logging.getLogger(__name__)


class MessageTemplates:
    USER_START = (
        "👋 Здравствуйте!\n"
        "Чем можем помочь? Опишите ваш вопрос, и мы скоро ответим.\n\n"
        "ℹ️ Можете отправлять фото, видео и документы."
    )
    
    USER_START_EXISTING = (
        "👋 Здравствуйте!\n"
        "Чем можем помочь? Опишите ваш вопрос, и мы скоро ответим.\n\n"
        "ℹ️ Можете отправлять фото, видео и документы."
    )
    
    SUPPORT_USER_INFO = (
        "ℹ️ Новое обращение от пользователя\n\n"
        "👤 Имя: {user_name}\n"
        "🆔 ID: {user_id}\n\n"
        "💬 Ожидайте сообщения от пользователя или начните диалог первым."
    )
    
    ERROR_CREATION = "❌ Ошибка создания обращения. Попробуйте позже."
    ERROR_NOT_STARTED = "⚠️ Сначала используйте команду /start"
    ERROR_SEND_MESSAGE = "❌ Ошибка отправки сообщения. Попробуйте позже."
    ERROR_USER_NOT_FOUND = "❌ Пользователь не найден для данного топика"
    ERROR_SEND_TO_USER = "❌ Ошибка отправки сообщения пользователю"


def get_user_button(user_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Пользователь",
                    url=f"tg://user?id={user_id}"
                )
            ]
        ]
    )
    return keyboard


def register_handlers(
    dp: Dispatcher,
    db_manager: DatabaseManager,
    config: Config
) -> None:
    
    @dp.message(Command("start"), F.chat.type == ChatType.PRIVATE)
    async def cmd_start(message: Message, bot: Bot) -> None:
        if not message.from_user:
            return
        
        user_id: int = message.from_user.id
        user_name: str = message.from_user.full_name or f"User{user_id}"
        
        try:
            existing_topic: Optional[int] = await db_manager.get_user_topic(user_id)
            
            if existing_topic:
                await message.answer(MessageTemplates.USER_START_EXISTING)
                return
            
            topic = await bot.create_forum_topic(
                chat_id=config.support_group_id,
                name=user_name[:128]
            )
            
            topic_id: int = topic.message_thread_id
            
            await db_manager.create_user_topic(user_id, topic_id)
            
            await message.answer(MessageTemplates.USER_START)
            
            await bot.send_message(
                chat_id=config.support_group_id,
                message_thread_id=topic_id,
                text=MessageTemplates.SUPPORT_USER_INFO.format(
                    user_id=user_id,
                    user_name=user_name
                ),
                reply_markup=get_user_button(user_id)
            )
            
        except TelegramBadRequest as e:
            logger.error(
                f"Telegram ошибка при создании топика для user_id={user_id}: {e}"
            )
            await message.answer(MessageTemplates.ERROR_CREATION)
        except DatabaseError as e:
            logger.error(f"БД ошибка для user_id={user_id}: {e}")
            await message.answer(MessageTemplates.ERROR_CREATION)
        except Exception as e:
            logger.exception(f"Неизвестная ошибка для user_id={user_id}: {e}")
            await message.answer(MessageTemplates.ERROR_CREATION)
    
    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def handle_user_message(message: Message, bot: Bot) -> None:
        if not message.from_user:
            return
        
        user_id: int = message.from_user.id
        
        try:
            topic_id: Optional[int] = await db_manager.get_user_topic(user_id)
            
            if not topic_id:
                await message.answer(MessageTemplates.ERROR_NOT_STARTED)
                return
            
            await bot.copy_message(
                chat_id=config.support_group_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                message_thread_id=topic_id
            )
            
        except TelegramAPIError as e:
            logger.error(
                f"Telegram ошибка отправки в поддержку от user_id={user_id}: {e}"
            )
            await message.answer(MessageTemplates.ERROR_SEND_MESSAGE)
        except DatabaseError as e:
            logger.error(f"БД ошибка для user_id={user_id}: {e}")
            await message.answer(MessageTemplates.ERROR_SEND_MESSAGE)
        except Exception as e:
            logger.exception(
                f"Неизвестная ошибка отправки сообщения от user_id={user_id}: {e}"
            )
            await message.answer(MessageTemplates.ERROR_SEND_MESSAGE)
    
    @dp.message(
        F.chat.id == config.support_group_id,
        F.message_thread_id.as_("thread_id")
    )
    async def handle_support_reply(
        message: Message,
        bot: Bot,
        thread_id: int
    ) -> None:
        try:
            user_id: Optional[int] = await db_manager.get_user_by_topic(thread_id)
            
            if not user_id:
                await message.reply(MessageTemplates.ERROR_USER_NOT_FOUND)
                return
            
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            
        except TelegramAPIError as e:
            logger.error(
                f"Telegram ошибка отправки пользователю user_id={user_id}: {e}"
            )
            await message.reply(MessageTemplates.ERROR_SEND_TO_USER)
        except DatabaseError as e:
            logger.error(f"БД ошибка для topic_id={thread_id}: {e}")
            await message.reply(MessageTemplates.ERROR_SEND_TO_USER)
        except Exception as e:
            logger.exception(
                f"Неизвестная ошибка отправки user_id={user_id}: {e}"
            )
            await message.reply(MessageTemplates.ERROR_SEND_TO_USER)
