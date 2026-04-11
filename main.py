import asyncio
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, add_user, get_statistics, get_all_users

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Константа для пути БД
DB_PATH = "database.db"

# Состояния FSM
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_vip_id = State()
    waiting_for_vip_days = State()

# Инлайн-клавиатура для админа
admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stat"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")
        ],
        [
            InlineKeyboardButton(text="🎁 Выдать VIP", callback_data="give_vip")
        ]
    ]
)

async def on_startup():
    """
    Функция, запускаемая при старте бота.
    Инициализирует базу данных.
    """
    await init_db(DB_PATH)
    logging.info("Database initialized and bot is starting up...")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Хэндлер команды /start. Приветствует пользователя и сохраняет его в БД.
    """
    await add_user(DB_PATH, message.from_user.id)
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\nВы успешно зарегистрированы в системе.")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """
    Хэндлер команды /admin. Доступен только для ADMIN_ID.
    """
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🎛 Панель управления",
            reply_markup=admin_kb
        )
    else:
        await message.answer("У вас нет прав доступа к этой команде. 🚫")

@dp.callback_query(F.data == "stat")
async def callback_statistics(callback: types.CallbackQuery):
    """
    Хэндлер для кнопки 'Статистика'.
    """
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return

    user_count, total_revenue = await get_statistics(DB_PATH)
    
    text = (
        f"📈 *Статистика:*\n"
        f"👥 Пользователей: {user_count}\n"
        f"💸 Доход: ${total_revenue:.2f}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "broadcast")
async def callback_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """
    Хэндлер для кнопки 'Рассылка'. Переводит админа в режим ожидания текста.
    """
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.edit_text(
        "📝 Отправь мне текст для рассылки всем пользователям."
    )
    await callback.answer()

@dp.callback_query(F.data == "give_vip")
async def callback_give_vip(callback: types.CallbackQuery, state: FSMContext):
    """
    Хэндлер для кнопки 'Выдать VIP'. Запрашивает ID пользователя.
    """
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_vip_id)
    await callback.message.edit_text("👤 Отправь Telegram ID пользователя:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    """
    Хэндлер получения текста рассылки и её отправки всем пользователям.
    """
    if message.from_user.id != ADMIN_ID:
        return

    users = await get_all_users(DB_PATH)
    count = 0
    
    await message.answer("🚀 Рассылка началась...")

    for user_id in users:
        try:
            # Используем send_copy для поддержки медиа (картинки, видео и т.д.)
            await message.send_copy(chat_id=user_id)
            count += 1
        except Exception as e:
            logging.error(f"Failed to send to {user_id}: {e}")
            continue

    await message.answer(f"✅ Рассылка успешно завершена!\nДоставлено: {count} пользователям.")
    await state.clear()

@dp.message(AdminStates.waiting_for_vip_id)
async def process_vip_id(message: types.Message, state: FSMContext):
    """
    Хэндлер получения ID пользователя для выдачи VIP.
    """
    if message.from_user.id != ADMIN_ID:
        return

    if not message.text.isdigit():
        await message.answer("❌ Ошибка! ID должен состоять только из цифр. Попробуй еще раз:")
        return

    user_id = int(message.text)
    await state.update_data(target_user_id=user_id)
    await message.answer("⏳ На сколько дней выдать VIP?")
    await state.set_state(AdminStates.waiting_for_vip_days)

@dp.message(AdminStates.waiting_for_vip_days)
async def process_vip_days(message: types.Message, state: FSMContext):
    """
    Хэндлер получения количества дней и завершения выдачи VIP.
    """
    if message.from_user.id != ADMIN_ID:
        return

    if not message.text.isdigit():
        await message.answer("❌ Ошибка! Количество дней должно быть числом. Попробуй еще раз:")
        return

    days = int(message.text)
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await message.answer("❌ Ошибка! Данные потеряны. Начни процесс заново через /admin.")
        await state.clear()
        return

    end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        from database import add_subscription
        await add_subscription(DB_PATH, target_user_id, "VIP", end_date)

        await message.answer(f"✅ VIP успешно выдан пользователю {target_user_id} на {days} дней!")

        try:
            await bot.send_message(target_user_id, f"🎉 Администратор выдал вам VIP-доступ на {days} дней!")
        except Exception as e:
            logging.error(f"Could not notify user {target_user_id}: {e}")

    except Exception as e:
        logging.error(f"Error during VIP issuance: {e}")
        await message.answer("❌ Произошла ошибка при выдаче VIP.")
    
    finally:
        await state.clear()

async def main():
    # Регистрация функции on_startup через dp.startup
    dp.startup.register(on_startup)
    
    # Запуск процесса polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())