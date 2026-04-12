import asyncio
import logging
import asyncio
from datetime import datetime, timedelta
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo, 
    LabeledPrice, 
    PreCheckoutQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, ADMIN_ID, PAYMENT_TOKEN, WEB_APP_URL, CHANNEL_ID
from database import (
    init_db, 
    add_user, 
    get_statistics, 
    get_all_users, 
    add_subscription,
    get_user_subscription,
    get_expired_subscriptions,
    delete_subscription
)

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

async def on_startup(bot: Bot):
    """
    Функция, запускаемая при старте бота.
    Инициализирует базу данных и запускает фоновые задачи.
    """
    await init_db(DB_PATH)
    # Запуск фоновой задачи проверки подписок
    asyncio.create_task(check_expirations(bot, CHANNEL_ID))
    logging.info("Database initialized and background tasks started...")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """
    Хэндлер команды /profile. Показывает статус подписки пользователя.
    """
    subscription_end_date = await get_user_subscription(DB_PATH, message.from_user.id)
    
    if subscription_end_date:
        await message.answer(f"✨ Ваша подписка активна до: {subscription_end_date}")
    else:
        await message.answer("❌ У вас нет подписки. Нажмите /start для покупки.")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Хэндлер команды /start. Приветствует пользователя и сохраняет его в БД.
    """
    await add_user(DB_PATH, message.from_user.id)
    
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"Привет, {message.from_user.full_name}! 👋\nВы администратор системы.")
    else:
        # Создаем кнопку для открытия Mini App (ReplyKeyboardMarkup обязательна для sendData)
        buy_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⭐️ Купить VIP", web_app=WebAppInfo(url=WEB_APP_URL))]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Добро пожаловать! Нажмите кнопку ниже, чтобы выбрать VIP тариф.",
            reply_markup=buy_kb
        )

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

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    """
    Хэндлер данных из Mini App. Выставляет счет на оплату.
    """
    try:
        data = json.loads(message.web_app_data.data)
        plan_id = data.get('id')
        price = data.get('price')
        duration = data.get('duration')

        await message.answer_invoice(
            title='VIP Подписка',
            description=f'Тариф на {duration} дней',
            payload=f'vip_{duration}',
            provider_token=PAYMENT_TOKEN,
            currency='USD',
            prices=[LabeledPrice(label='VIP', amount=int(price * 100))]
        )
    except Exception as e:
        logging.error(f"Error processing web_app_data: {e}")
        await message.answer("❌ Произошла ошибка при обработке данных из Mini App.")

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Обязательный хэндлер проверки платежа перед оплатой.
    """
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    """
    Хэндлер успешной оплаты. Активирует подписку и выдает одноразовую ссылку.
    """
    try:
        # Извлекаем duration из payload (формат vip_{duration})
        payload = message.successful_payment.invoice_payload
        duration = int(payload.split('_')[1])

        # Активируем подписку в БД
        await add_subscription(DB_PATH, message.from_user.id, 'VIP', duration)

        # Пытаемся создать одноразовую ссылку
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID, 
                member_limit=1
            )
            response_text = (
                f"🎉 Оплата прошла успешно! Ваш VIP активирован на {duration} дней.\n"
                f"🔗 Вот ваша одноразовая персональная ссылка "
                f"(она сгорит после 1 использования): {invite_link.invite_link}"
            )
        except Exception as e:
            logging.error(f"Error creating invite link: {e}")
            response_text = (
                f"🎉 Оплата прошла успешно! Ваш VIP активирован на {duration} дней.\n"
                f"⚠️ Не удалось сгенерировать персональную ссылку. "
                f"Пожалуйста, вступите в канал вручную: https://t.me/Ockynua"
            )

        await message.answer(response_text)

    except Exception as e:
        logging.error(f"Error during successful payment processing: {e}")
        await message.answer("❌ Произошла ошибка при активации подписки после оплаты.")

async def check_expirations(bot: Bot, channel_id: int):
    """
    Фоновая задача для проверки и удаления просроченных подписок.
    """
    while True:
        try:
            expired_users = await get_expired_subscriptions(DB_PATH)
            for user_id in expired_users:
                try:
                    # Выгоняем из канала (ban + unban)
                    await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)
                    await bot.unban_chat_member(chat_id=channel_id, user_id=user_id)
                    
                    # Удаляем из БД
                    await delete_subscription(DB_PATH, user_id)
                    
                    # Уведомляем пользователя
                    await bot.send_message(
                        user_id, 
                        "⚠️ Ваша VIP подписка закончилась. Вы были исключены из канала. "
                        "Продлите подписку через /start"
                    )
                except Exception as e:
                    logging.error(f"Error processing expired user {user_id}: {e}")
            
        except Exception as e:
            logging.error(f"Error in check_expirations loop: {e}")
        
        await asyncio.sleep(60)

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