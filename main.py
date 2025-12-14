import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from config import BOT_TOKEN, FARM_TYPES, NFT_GIFTS, GAME_NAME, ADMIN_IDS
from database import (
    init_db, get_or_create_user, get_user_stars, 
    buy_farm, get_user_farms, buy_nft, get_user_nfts,
    calculate_total_boost, collect_farm_income,
    register_referral, give_referral_reward, get_referral_count,
    create_auction, get_active_auctions, place_bid, end_auction,
    activate_farms, is_banned, ban_user, unban_user,
    admin_add_stars, admin_add_farm, admin_add_nft,
    get_all_users, get_all_chats, add_chat, spend_stars, add_stars
)
from keyboards import (
    get_main_menu, get_farm_shop_keyboard, 
    get_nft_shop_keyboard, get_back_keyboard, get_auction_keyboard,
    get_admin_menu, get_casino_menu, get_farm_select_keyboard, get_nft_select_keyboard
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверка на бан
    if await is_banned(user_id):
        await message.answer("❌ Вы заблокированы в боте!")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Проверяем реферальную ссылку
    is_new_user = False
    if args:
        try:
            referrer_id = int(args[0])
            # Запрещаем переход по своей ссылке
            if referrer_id != user_id:
                is_new_user = await register_referral(referrer_id, user_id)
                if is_new_user:
                    await give_referral_reward(user_id)
                    # Уведомляем реферера
                    try:
                        from config import REFERRAL_REWARD
                        referrer_name = message.from_user.full_name or f"@{message.from_user.username}" if message.from_user.username else "Пользователь"
                        referrer_mention = f"@{message.from_user.username}" if message.from_user.username else referrer_name
                        notification = (
                            f"🎉 Новый пользователь {referrer_mention} зарегистрировался по вашей реферальной ссылке!\n"
                            f"💰 Вам зачислено {REFERRAL_REWARD} ⭐"
                        )
                        await bot.send_message(referrer_id, notification)
                    except:
                        pass
        except ValueError:
            pass
    
    user = await get_or_create_user(user_id)
    
    welcome_text = (
        f"🌟 Добро пожаловать в {GAME_NAME}!\n\n"
        "💰 Валюта: Звезды ⭐\n"
        "🌾 Покупайте фермы, которые приносят звезды\n"
        "🎁 Покупайте NFT подарки для буста к доходу\n\n"
    )
    
    if is_new_user:
        from config import REFERRAL_REWARD
        welcome_text += f"🎉 Вы получили {REFERRAL_REWARD} ⭐ за регистрацию по реферальной ссылке!\n\n"
    
    welcome_text += "Используйте меню для навигации или команду /help для списка команд!"
    
    # В группах не показываем клавиатуру
    if message.chat.type == "private":
        await message.answer(welcome_text, reply_markup=get_main_menu())
    else:
        await message.reply(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        f"📖 Справка по командам {GAME_NAME}\n\n"
        "🔹 /start - Начать игру или зарегистрироваться\n"
        "🔹 /help - Показать эту справку\n"
        "🔹 /profile - Показать ваш профиль\n"
        "🔹 /farms - Показать ваши фермы\n"
        "🔹 /shop - Открыть магазин ферм\n"
        "🔹 /nft - Открыть магазин NFT\n"
        "🔹 /collect - Собрать доход с ферм\n"
        "🔹 /activate - Активировать фермы (каждые 6 часов)\n"
        "🔹 /referral - Получить реферальную ссылку\n"
        "🔹 /auction - Показать активные аукционы\n\n"
        "💡 Важно:\n"
        "• Фермы нужно активировать каждые 6 часов\n"
        "• Только активированные фермы приносят доход\n"
        "• Используйте NFT для увеличения дохода\n"
        "• Приглашайте друзей по реферальной ссылке!"
    )
    
    if message.chat.type == "private":
        await message.answer(help_text)
    else:
        await message.reply(help_text)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Команда /profile"""
    await show_profile_handler(message)

@dp.message(F.text == "⭐ Мой профиль")
async def show_profile(message: Message):
    """Показать профиль пользователя"""
    await show_profile_handler(message)

async def show_profile_handler(message: Message):
    """Обработчик показа профиля"""
    user_id = message.from_user.id
    user = await get_or_create_user(user_id)
    stars = user['stars']
    
    farms = await get_user_farms(user_id)
    nfts = await get_user_nfts(user_id)
    boost = await calculate_total_boost(user_id)
    referrals = await get_referral_count(user_id)
    
    # Подсчитываем активные фермы
    from datetime import datetime
    active_farms = 0
    for farm in farms:
        is_active = farm.get('is_active', 0)
        if is_active:
            last_activated = farm.get('last_activated')
            if last_activated:
                last_activated_dt = datetime.fromisoformat(last_activated)
                hours_passed = (datetime.now() - last_activated_dt).total_seconds() / 3600
                if hours_passed < 6:
                    active_farms += 1
    
    profile_text = (
        f"👤 Ваш профиль\n\n"
        f"⭐ Звезд: {stars}\n"
        f"🌾 Ферм: {len(farms)} (активных: {active_farms})\n"
        f"🎁 NFT: {len(nfts)}\n"
        f"⚡ Буст к доходу: {int((boost - 1) * 100)}%\n"
        f"🔗 Рефералов: {referrals}\n\n"
    )
    
    if farms:
        profile_text += "Ваши фермы:\n"
        farm_counts = {}
        for farm in farms:
            farm_type = farm['farm_type']
            farm_counts[farm_type] = farm_counts.get(farm_type, 0) + 1
        
        for farm_type, count in farm_counts.items():
            if farm_type in FARM_TYPES:
                profile_text += f"  {FARM_TYPES[farm_type]['name']}: {count} шт.\n"
    
    if nfts:
        profile_text += "\nВаши NFT:\n"
        nft_counts = {}
        for nft in nfts:
            nft_type = nft['nft_type']
            nft_counts[nft_type] = nft_counts.get(nft_type, 0) + 1
        
        for nft_type, count in nft_counts.items():
            if nft_type in NFT_GIFTS:
                profile_text += f"  {NFT_GIFTS[nft_type]['name']}: {count} шт.\n"
    
    if message.chat.type == "private":
        await message.answer(profile_text)
    else:
        await message.reply(profile_text)

@dp.message(Command("farms"))
async def cmd_farms(message: Message):
    """Команда /farms"""
    await show_farms_handler(message)

@dp.message(F.text == "🌾 Мои фермы")
async def show_farms(message: Message):
    """Показать фермы пользователя"""
    await show_farms_handler(message)

async def show_farms_handler(message: Message):
    """Обработчик показа ферм"""
    user_id = message.from_user.id
    farms = await get_user_farms(user_id)
    
    if not farms:
        response = "У вас пока нет ферм. Купите их в магазине! 🛒"
        if message.chat.type == "private":
            await message.answer(response)
        else:
            await message.reply(response)
        return
    
    from datetime import datetime
    farm_counts = {}
    active_count = 0
    inactive_count = 0
    
    for farm in farms:
        farm_type = farm['farm_type']
        farm_counts[farm_type] = farm_counts.get(farm_type, {'total': 0, 'active': 0})
        farm_counts[farm_type]['total'] += 1
        
        is_active = farm.get('is_active', 0)
        if is_active:
            last_activated = farm.get('last_activated')
            if last_activated:
                last_activated_dt = datetime.fromisoformat(last_activated)
                hours_passed = (datetime.now() - last_activated_dt).total_seconds() / 3600
                if hours_passed < 6:
                    farm_counts[farm_type]['active'] += 1
                    active_count += 1
                else:
                    inactive_count += 1
            else:
                inactive_count += 1
        else:
            inactive_count += 1
    
    farms_text = "🌾 Ваши фермы:\n\n"
    total_income = 0
    total_active_income = 0
    
    for farm_type, data in farm_counts.items():
        if farm_type in FARM_TYPES:
            farm_data = FARM_TYPES[farm_type]
            total = data['total']
            active = data['active']
            inactive = total - active
            
            income = farm_data['income_per_hour'] * active  # Только активные
            total_active_income += income
            total_income += farm_data['income_per_hour'] * total
            
            income_per_min = round(income / 60, 2)
            status = "✅" if active > 0 else "❌"
            farms_text += f"{status} {farm_data['name']}: {total} шт. (активных: {active})\n"
            if active > 0:
                farms_text += f"  Доход: {income_per_min} ⭐/мин | {income} ⭐/час\n\n"
            else:
                farms_text += f"  ⚠️ Требуется активация (/activate)\n\n"
    
    boost = await calculate_total_boost(user_id)
    if boost > 1.0:
        total_income_boosted = int(total_active_income * boost)
        total_income_boosted_per_min = round(total_income_boosted / 60, 2)
        farms_text += f"📊 Доход (активные): {round(total_active_income / 60, 2)} ⭐/мин | {total_active_income} ⭐/час\n"
        farms_text += f"⚡ С бустом: {total_income_boosted_per_min} ⭐/мин | {total_income_boosted} ⭐/час\n"
    else:
        total_income_per_min = round(total_active_income / 60, 2)
        farms_text += f"📊 Доход (активные): {total_income_per_min} ⭐/мин | {total_active_income} ⭐/час\n"
    
    if inactive_count > 0:
        farms_text += f"\n⚠️ {inactive_count} ферм требуют активации! Используйте /activate"
    
    if message.chat.type == "private":
        await message.answer(farms_text)
    else:
        await message.reply(farms_text)

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    """Команда /shop"""
    await show_farm_shop_handler(message)

@dp.message(F.text == "🛒 Магазин ферм")
async def show_farm_shop(message: Message):
    """Показать магазин ферм"""
    await show_farm_shop_handler(message)

async def show_farm_shop_handler(message: Message):
    """Обработчик магазина ферм"""
    user_id = message.from_user.id
    stars = await get_user_stars(user_id)
    
    shop_text = f"🛒 Магазин ферм\n\n⭐ Ваши звезды: {stars}\n\n"
    
    for farm_id, farm_data in FARM_TYPES.items():
        income_per_min = round(farm_data['income_per_hour'] / 60, 2)
        shop_text += (
            f"{farm_data['name']}\n"
            f"💰 Цена: {farm_data['price']} ⭐\n"
            f"📈 Доход: {income_per_min} ⭐/мин | {farm_data['income_per_hour']} ⭐/час\n\n"
        )
    
    if message.chat.type == "private":
        await message.answer(shop_text, reply_markup=get_farm_shop_keyboard())
    else:
        await message.reply(shop_text + "\n💡 В группах используйте команды для покупки")

@dp.message(Command("nft"))
async def cmd_nft(message: Message):
    """Команда /nft"""
    await show_nft_shop_handler(message)

@dp.message(F.text == "🎁 Магазин NFT")
async def show_nft_shop(message: Message):
    """Показать магазин NFT"""
    await show_nft_shop_handler(message)

async def show_nft_shop_handler(message: Message):
    """Обработчик магазина NFT"""
    user_id = message.from_user.id
    stars = await get_user_stars(user_id)
    
    shop_text = (
        f"🎁 Магазин NFT подарков\n\n"
        f"⭐ Ваши звезды: {stars}\n\n"
        f"NFT дают буст к доходу с ферм!\n\n"
    )
    
    for nft_id, nft_data in NFT_GIFTS.items():
        boost_text = f"+{int((nft_data['boost'] - 1) * 100)}%"
        shop_text += (
            f"{nft_data['name']}\n"
            f"💰 Цена: {nft_data['price']} ⭐\n"
            f"⚡ Буст: {boost_text}\n\n"
        )
    
    if message.chat.type == "private":
        await message.answer(shop_text, reply_markup=get_nft_shop_keyboard())
    else:
        await message.reply(shop_text + "\n💡 В группах используйте команды для покупки")

@dp.message(Command("activate"))
async def cmd_activate(message: Message):
    """Команда /activate - активировать фермы"""
    user_id = message.from_user.id
    farms = await get_user_farms(user_id)
    
    if not farms:
        response = "У вас нет ферм для активации! Купите фермы в магазине. 🛒"
        if message.chat.type == "private":
            await message.answer(response)
        else:
            await message.reply(response)
        return
    
    activated, total = await activate_farms(user_id)
    
    if activated > 0:
        response = (
            f"✅ Активировано ферм: {activated} из {total}\n\n"
            f"🌾 Ваши фермы активны на следующие 6 часов!\n"
            f"💡 Не забудьте собрать доход командой /collect"
        )
    else:
        from datetime import datetime
        # Проверяем, когда можно будет активировать снова
        can_activate_soon = False
        min_hours_left = 6
        for farm in farms:
            last_activated = farm.get('last_activated')
            if last_activated:
                last_activated_dt = datetime.fromisoformat(last_activated)
                hours_passed = (datetime.now() - last_activated_dt).total_seconds() / 3600
                hours_left = 6 - hours_passed
                if hours_left > 0:
                    min_hours_left = min(min_hours_left, hours_left)
                    can_activate_soon = True
        
        if can_activate_soon:
            hours = int(min_hours_left)
            minutes = int((min_hours_left - hours) * 60)
            response = (
                f"⏰ Все фермы уже активированы!\n\n"
                f"🔄 Следующая активация через: {hours}ч {minutes}м"
            )
        else:
            response = (
                f"✅ Все фермы активированы!\n\n"
                f"💡 Фермы активны на 6 часов. Используйте /collect для сбора дохода."
            )
    
    if message.chat.type == "private":
        await message.answer(response)
    else:
        await message.reply(response)

@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    """Команда /collect"""
    await collect_income_handler(message)

@dp.message(F.text == "💰 Собрать доход")
async def collect_income(message: Message):
    """Собрать доход с ферм"""
    await collect_income_handler(message)

async def collect_income_handler(message: Message):
    """Обработчик сбора дохода"""
    user_id = message.from_user.id
    farms = await get_user_farms(user_id)
    
    if not farms:
        response = "У вас нет ферм для сбора дохода! Купите фермы в магазине. 🛒"
        if message.chat.type == "private":
            await message.answer(response)
        else:
            await message.reply(response)
        return
    
    income = await collect_farm_income(user_id)
    stars = await get_user_stars(user_id)
    boost = await calculate_total_boost(user_id)
    
    # Рассчитываем текущий доход в минуту и час (только активные фермы)
    from datetime import datetime
    total_income_per_hour = 0
    active_farms_count = 0
    for farm in farms:
        is_active = farm.get('is_active', 0)
        if is_active:
            last_activated = farm.get('last_activated')
            if last_activated:
                last_activated_dt = datetime.fromisoformat(last_activated)
                hours_passed = (datetime.now() - last_activated_dt).total_seconds() / 3600
                if hours_passed < 6:
                    farm_type = farm['farm_type']
                    if farm_type in FARM_TYPES:
                        total_income_per_hour += FARM_TYPES[farm_type]['income_per_hour']
                        active_farms_count += 1
    
    total_income_per_hour_boosted = int(total_income_per_hour * boost)
    total_income_per_min_boosted = round(total_income_per_hour_boosted / 60, 2)
    total_income_per_min = round(total_income_per_hour / 60, 2)
    
    if income > 0:
        boost_text = ""
        if boost > 1.0:
            boost_text = f"\n⚡ Буст от NFT: {int((boost - 1) * 100)}%"
        
        response = (
            f"💰 Вы собрали доход!\n\n"
            f"⭐ Получено: {income} звезд{boost_text}\n"
            f"💎 Всего звезд: {stars}\n\n"
            f"📊 Текущий доход ({active_farms_count} активных ферм):\n"
            f"   {total_income_per_min} ⭐/мин | {total_income_per_hour} ⭐/час"
        )
        if boost > 1.0:
            response += f"\n   ⚡ С бустом: {total_income_per_min_boosted} ⭐/мин | {total_income_per_hour_boosted} ⭐/час"
    else:
        if active_farms_count == 0:
            response = (
                f"⚠️ У вас нет активных ферм!\n"
                f"💎 Ваши звезды: {stars}\n\n"
                f"💡 Используйте /activate для активации ферм"
            )
        else:
            response = (
                f"⏰ Доход еще не накоплен.\n"
                f"💎 Ваши звезды: {stars}\n\n"
                f"📊 Текущий доход ({active_farms_count} активных ферм):\n"
                f"   {total_income_per_min} ⭐/мин | {total_income_per_hour} ⭐/час"
            )
            if boost > 1.0:
                response += f"\n   ⚡ С бустом: {total_income_per_min_boosted} ⭐/мин | {total_income_per_hour_boosted} ⭐/час"
            response += "\n\nДоход накапливается каждый час!"
    
    if message.chat.type == "private":
        await message.answer(response)
    else:
        await message.reply(response)

@dp.callback_query(F.data.startswith("buy_farm_"))
async def handle_buy_farm(callback: CallbackQuery):
    """Обработчик покупки фермы"""
    farm_id = callback.data.split("_")[2]
    
    if farm_id not in FARM_TYPES:
        await callback.answer("Ошибка: неверный тип фермы", show_alert=True)
        return
    
    user_id = callback.from_user.id
    farm_data = FARM_TYPES[farm_id]
    
    success = await buy_farm(user_id, farm_id)
    
    if success:
        stars = await get_user_stars(user_id)
        await callback.answer(
            f"✅ Вы купили {farm_data['name']}!",
            show_alert=True
        )
        
        shop_text = f"🛒 Магазин ферм\n\n⭐ Ваши звезды: {stars}\n\n"
        shop_text += f"✅ Вы купили {farm_data['name']}!\n\n"
        
        for farm_id_item, farm_data_item in FARM_TYPES.items():
            income_per_min = round(farm_data_item['income_per_hour'] / 60, 2)
            shop_text += (
                f"{farm_data_item['name']}\n"
                f"💰 Цена: {farm_data_item['price']} ⭐\n"
                f"📈 Доход: {income_per_min} ⭐/мин | {farm_data_item['income_per_hour']} ⭐/час\n\n"
            )
        
        await callback.message.edit_text(shop_text, reply_markup=get_farm_shop_keyboard())
    else:
        stars = await get_user_stars(user_id)
        await callback.answer(
            f"❌ Недостаточно звезд! Нужно {farm_data['price']}, у вас {stars}",
            show_alert=True
        )

@dp.callback_query(F.data.startswith("buy_nft_"))
async def handle_buy_nft(callback: CallbackQuery):
    """Обработчик покупки NFT"""
    nft_id = callback.data.split("_")[2]
    
    if nft_id not in NFT_GIFTS:
        await callback.answer("Ошибка: неверный тип NFT", show_alert=True)
        return
    
    user_id = callback.from_user.id
    nft_data = NFT_GIFTS[nft_id]
    
    success = await buy_nft(user_id, nft_id)
    
    if success:
        stars = await get_user_stars(user_id)
        boost = await calculate_total_boost(user_id)
        boost_text = f"+{int((nft_data['boost'] - 1) * 100)}%"
        
        await callback.answer(
            f"✅ Вы купили {nft_data['name']}! Буст: {boost_text}",
            show_alert=True
        )
        
        shop_text = (
            f"🎁 Магазин NFT подарков\n\n"
            f"⭐ Ваши звезды: {stars}\n\n"
            f"✅ Вы купили {nft_data['name']}!\n"
            f"⚡ Общий буст: {int((boost - 1) * 100)}%\n\n"
        )
        
        for nft_id_item, nft_data_item in NFT_GIFTS.items():
            boost_item_text = f"+{int((nft_data_item['boost'] - 1) * 100)}%"
            shop_text += (
                f"{nft_data_item['name']}\n"
                f"💰 Цена: {nft_data_item['price']} ⭐\n"
                f"⚡ Буст: {boost_item_text}\n\n"
            )
        
        await callback.message.edit_text(shop_text, reply_markup=get_nft_shop_keyboard())
    else:
        stars = await get_user_stars(user_id)
        await callback.answer(
            f"❌ Недостаточно звезд! Нужно {nft_data['price']}, у вас {stars}",
            show_alert=True
        )

@dp.message(Command("referral"))
async def cmd_referral(message: Message):
    """Команда /referral"""
    await show_referral_link_handler(message)

@dp.message(F.text == "🔗 Реферальная ссылка")
async def show_referral_link(message: Message):
    """Показать реферальную ссылку"""
    await show_referral_link_handler(message)

async def show_referral_link_handler(message: Message):
    """Обработчик реферальной ссылки"""
    user_id = message.from_user.id
    referrals = await get_referral_count(user_id)
    
    from config import REFERRAL_REWARD
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    referral_text = (
        f"🔗 Ваша реферальная ссылка:\n\n"
        f"{referral_link}\n\n"
        f"💰 За каждого приглашенного друга вы получаете награду!\n"
        f"🎁 Новый пользователь получает {REFERRAL_REWARD} ⭐\n\n"
        f"👥 Приглашено друзей: {referrals}"
    )
    
    if message.chat.type == "private":
        await message.answer(referral_text)
    else:
        await message.reply(referral_text)

@dp.message(Command("auction"))
async def cmd_auction(message: Message):
    """Команда /auction"""
    await show_auctions_handler(message)

@dp.message(F.text == "🔨 Аукцион")
async def show_auctions(message: Message):
    """Показать активные аукционы"""
    await show_auctions_handler(message)

async def show_auctions_handler(message: Message):
    """Обработчик показа аукционов"""
    user_id = message.from_user.id
    
    # Проверяем и завершаем истекшие аукционы
    from datetime import datetime
    active_auctions = await get_active_auctions()
    for auction in active_auctions:
        end_time = datetime.fromisoformat(auction['end_time'])
        if datetime.now() >= end_time:
            await end_auction(auction['id'])
    
    auctions = await get_active_auctions()
    
    if not auctions:
        # Создаем несколько аукционов, если их нет
        from random import choice
        
        farm_types = list(FARM_TYPES.keys())[-4:]  # Последние 4 типа ферм
        for i in range(3):
            farm_type = choice(farm_types)
            farm_data = FARM_TYPES[farm_type]
            starting_price = farm_data['price'] // 2  # Начальная цена = половина обычной
            await create_auction(farm_type, starting_price, 24)
        
        auctions = await get_active_auctions()
    
    if not auctions:
        response = "Сейчас нет активных аукционов. Попробуйте позже!"
        if message.chat.type == "private":
            await message.answer(response)
        else:
            await message.reply(response)
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    auctions_text = "🔨 Активные аукционы:\n\n"
    keyboard_buttons = []
    
    for auction in auctions:
        farm_type = auction['farm_type']
        if farm_type in FARM_TYPES:
            farm_data = FARM_TYPES[farm_type]
            end_time = datetime.fromisoformat(auction['end_time'])
            time_left = end_time - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            minutes_left = int((time_left.total_seconds() % 3600) / 60)
            
            auctions_text += (
                f"{farm_data['name']}\n"
                f"💰 Текущая ставка: {auction['current_bid']} ⭐\n"
                f"⏰ Осталось: {hours_left}ч {minutes_left}м\n\n"
            )
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{farm_data['name']} - {auction['current_bid']} ⭐",
                    callback_data=f"auction_{auction['id']}"
                )
            ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if message.chat.type == "private":
        await message.answer(auctions_text, reply_markup=keyboard)
    else:
        await message.reply(auctions_text + "\n💡 В группах используйте команды для участия в аукционах")

@dp.callback_query(F.data.startswith("auction_"))
async def handle_auction_select(callback: CallbackQuery):
    """Обработчик выбора аукциона"""
    auction_id = int(callback.data.split("_")[1])
    
    auctions = await get_active_auctions()
    auction = next((a for a in auctions if a['id'] == auction_id), None)
    
    if not auction:
        await callback.answer("Аукцион не найден или уже завершен", show_alert=True)
        return
    
    from datetime import datetime
    farm_type = auction['farm_type']
    if farm_type in FARM_TYPES:
        farm_data = FARM_TYPES[farm_type]
        end_time = datetime.fromisoformat(auction['end_time'])
        time_left = end_time - datetime.now()
        hours_left = int(time_left.total_seconds() / 3600)
        minutes_left = int((time_left.total_seconds() % 3600) / 60)
        
        auction_text = (
            f"🔨 Аукцион: {farm_data['name']}\n\n"
            f"💰 Текущая ставка: {auction['current_bid']} ⭐\n"
            f"⏰ Осталось: {hours_left}ч {minutes_left}м\n\n"
            f"Выберите размер ставки:"
        )
        await callback.message.edit_text(auction_text, reply_markup=get_auction_keyboard(auction_id, auction['current_bid']))

@dp.callback_query(F.data.startswith("bid_"))
async def handle_bid(callback: CallbackQuery):
    """Обработчик ставки на аукционе"""
    parts = callback.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    
    user_id = callback.from_user.id
    success, message_text = await place_bid(auction_id, user_id, bid_amount)
    
    if success:
        await callback.answer(f"✅ {message_text}", show_alert=True)
        # Обновляем информацию об аукционе
        auctions = await get_active_auctions()
        auction = next((a for a in auctions if a['id'] == auction_id), None)
        if auction:
            from datetime import datetime
            farm_type = auction['farm_type']
            if farm_type in FARM_TYPES:
                farm_data = FARM_TYPES[farm_type]
                end_time = datetime.fromisoformat(auction['end_time'])
                time_left = end_time - datetime.now()
                hours_left = int(time_left.total_seconds() / 3600)
                minutes_left = int((time_left.total_seconds() % 3600) / 60)
                
                auction_text = (
                    f"🔨 Аукцион: {farm_data['name']}\n\n"
                    f"💰 Текущая ставка: {auction['current_bid']} ⭐\n"
                    f"⏰ Осталось: {hours_left}ч {minutes_left}м\n\n"
                    f"✅ Ваша ставка принята!\n\n"
                    f"Выберите размер следующей ставки:"
                )
                await callback.message.edit_text(auction_text, reply_markup=get_auction_keyboard(auction_id, auction['current_bid']))
    else:
        await callback.answer(f"❌ {message_text}", show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def handle_back(callback: CallbackQuery):
    """Обработчик кнопки назад"""
    await callback.answer()
    await callback.message.delete()

# Админ панель
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ панели!")
        return
    
    admin_text = (
        "🔐 Админ панель\n\n"
        "Выберите действие:"
    )
    await message.answer(admin_text, reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в админ меню"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text("🔐 Админ панель\n\nВыберите действие:", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_give_stars")
async def admin_give_stars_handler(callback: CallbackQuery):
    """Админ: выдать звезды"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "💰 Выдача звезд\n\n"
        "Отправьте в формате:\n"
        "<code>/give_stars user_id amount</code>\n\n"
        "Пример: /give_stars 123456789 1000",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    )

@dp.message(Command("give_stars"))
async def cmd_give_stars(message: Message):
    """Выдать звезды пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Использование: /give_stars user_id amount")
        return
    
    try:
        user_id = int(args[1])
        amount = int(args[2])
        await admin_add_stars(user_id, amount)
        await message.reply(f"✅ Пользователю {user_id} выдано {amount} ⭐")
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.callback_query(F.data == "admin_give_farm")
async def admin_give_farm_handler(callback: CallbackQuery):
    """Админ: выдать ферму"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "🌾 Выдача фермы\n\n"
        "Выберите тип фермы:",
        reply_markup=get_farm_select_keyboard()
    )

@dp.callback_query(F.data.startswith("admin_farm_"))
async def admin_give_farm_select(callback: CallbackQuery):
    """Админ: выбор фермы"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    farm_id = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"🌾 Выдача фермы\n\n"
        f"Тип: {FARM_TYPES[farm_id]['name']}\n\n"
        f"Отправьте ID пользователя:\n"
        f"<code>/give_farm {farm_id} user_id</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_give_farm")]
        ])
    )

@dp.message(Command("give_farm"))
async def cmd_give_farm(message: Message):
    """Выдать ферму пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Использование: /give_farm farm_id user_id")
        return
    
    try:
        farm_id = args[1]
        user_id = int(args[2])
        if farm_id not in FARM_TYPES:
            await message.reply("❌ Неверный тип фермы!")
            return
        await admin_add_farm(user_id, farm_id)
        await message.reply(f"✅ Пользователю {user_id} выдана {FARM_TYPES[farm_id]['name']}")
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.callback_query(F.data == "admin_give_nft")
async def admin_give_nft_handler(callback: CallbackQuery):
    """Админ: выдать NFT"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    await callback.message.edit_text(
        "🎁 Выдача NFT\n\n"
        "Выберите NFT:",
        reply_markup=get_nft_select_keyboard()
    )

@dp.callback_query(F.data.startswith("admin_nft_"))
async def admin_give_nft_select(callback: CallbackQuery):
    """Админ: выбор NFT"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    nft_id = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"🎁 Выдача NFT\n\n"
        f"Тип: {NFT_GIFTS[nft_id]['name']}\n\n"
        f"Отправьте ID пользователя:\n"
        f"<code>/give_nft {nft_id} user_id</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_give_nft")]
        ])
    )

@dp.message(Command("give_nft"))
async def cmd_give_nft(message: Message):
    """Выдать NFT пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Использование: /give_nft nft_id user_id")
        return
    
    try:
        nft_id = args[1]
        user_id = int(args[2])
        if nft_id not in NFT_GIFTS:
            await message.reply("❌ Неверный тип NFT!")
            return
        await admin_add_nft(user_id, nft_id)
        await message.reply(f"✅ Пользователю {user_id} выдано {NFT_GIFTS[nft_id]['name']}")
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    """Забанить пользователя"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("Использование: /ban user_id [причина]")
        return
    
    try:
        user_id = int(args[1])
        reason = args[2] if len(args) > 2 else "Нарушение правил"
        await ban_user(user_id, reason, message.from_user.id)
        await message.reply(f"✅ Пользователь {user_id} забанен. Причина: {reason}")
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    """Разбанить пользователя"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /unban user_id")
        return
    
    try:
        user_id = int(args[1])
        await unban_user(user_id)
        await message.reply(f"✅ Пользователь {user_id} разбанен")
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Рассылка всем пользователям"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение для рассылки")
        return
    
    text = message.reply_to_message.text or message.reply_to_message.caption
    if not text:
        await message.reply("Сообщение должно содержать текст")
        return
    
    users = await get_all_users()
    chats = await get_all_chats()
    
    sent = 0
    failed = 0
    
    await message.reply(f"📢 Начинаю рассылку...\nПользователей: {len(users)}\nЧатов: {len(chats)}")
    
    # Рассылка пользователям
    for user in users:
        try:
            await bot.send_message(user['user_id'], text)
            sent += 1
        except:
            failed += 1
    
    # Рассылка в чаты
    for chat in chats:
        try:
            await bot.send_message(chat['chat_id'], text)
            sent += 1
        except:
            failed += 1
    
    await message.reply(f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")

# Казино
@dp.message(F.text == "🎰 Казино")
async def show_casino(message: Message):
    """Показать казино"""
    user_id = message.from_user.id
    if await is_banned(user_id):
        return
    
    stars = await get_user_stars(user_id)
    casino_text = (
        f"🎰 Казино\n\n"
        f"⭐ Ваши звезды: {stars}\n\n"
        f"Выберите игру:"
    )
    await message.answer(casino_text, reply_markup=get_casino_menu())

@dp.callback_query(F.data == "casino_dice")
async def casino_dice(callback: CallbackQuery):
    """Игра в кости"""
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer("❌ Вы заблокированы!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎲 Кости\n\n"
        "Ставка: удвоение\n\n"
        "Отправьте сумму ставки:\n"
        "<code>/dice amount</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )

@dp.message(Command("dice"))
async def cmd_dice(message: Message):
    """Игра в кости"""
    user_id = message.from_user.id
    if await is_banned(user_id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /dice amount")
        return
    
    try:
        bet = int(args[1])
        stars = await get_user_stars(user_id)
        
        if bet < 10:
            await message.reply("❌ Минимальная ставка: 10 ⭐")
            return
        
        if bet > stars:
            await message.reply("❌ Недостаточно звезд!")
            return
        
        await spend_stars(user_id, bet)
        
        import random
        player_dice = random.randint(1, 6)
        bot_dice = random.randint(1, 6)
        
        if player_dice > bot_dice:
            win = bet * 2
            await add_stars(user_id, win)
            await message.reply(
                f"🎲 Вы: {player_dice}\n"
                f"🎲 Бот: {bot_dice}\n\n"
                f"✅ Вы выиграли {win} ⭐!"
            )
        else:
            await message.reply(
                f"🎲 Вы: {player_dice}\n"
                f"🎲 Бот: {bot_dice}\n\n"
                f"❌ Вы проиграли {bet} ⭐"
            )
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.callback_query(F.data == "casino_slots")
async def casino_slots_handler(callback: CallbackQuery):
    """Игра в слоты"""
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer("❌ Вы заблокированы!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎰 Слоты\n\n"
        "Ставка: утроение\n\n"
        "Отправьте сумму ставки:\n"
        "<code>/slots amount</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )

@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    """Игра в слоты"""
    user_id = message.from_user.id
    if await is_banned(user_id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /slots amount")
        return
    
    try:
        bet = int(args[1])
        stars = await get_user_stars(user_id)
        
        if bet < 10:
            await message.reply("❌ Минимальная ставка: 10 ⭐")
            return
        
        if bet > stars:
            await message.reply("❌ Недостаточно звезд!")
            return
        
        await spend_stars(user_id, bet)
        
        import random
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)
        
        if slot1 == slot2 == slot3:
            win = bet * 3
            await add_stars(user_id, win)
            await message.reply(
                f"🎰 [{slot1}] [{slot2}] [{slot3}]\n\n"
                f"🎉 ДЖЕКПОТ!\n"
                f"✅ Вы выиграли {win} ⭐!"
            )
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            win = bet * 2
            await add_stars(user_id, win)
            await message.reply(
                f"🎰 [{slot1}] [{slot2}] [{slot3}]\n\n"
                f"✅ Вы выиграли {win} ⭐!"
            )
        else:
            await message.reply(
                f"🎰 [{slot1}] [{slot2}] [{slot3}]\n\n"
                f"❌ Вы проиграли {bet} ⭐"
            )
    except ValueError:
        await message.reply("❌ Неверный формат!")

@dp.callback_query(F.data == "casino_roulette")
async def casino_roulette_handler(callback: CallbackQuery):
    """Игра в рулетку"""
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer("❌ Вы заблокированы!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎯 Рулетка\n\n"
        "Ставка: учетверение\n\n"
        "Отправьте сумму ставки:\n"
        "<code>/roulette amount</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )

@dp.message(Command("roulette"))
async def cmd_roulette(message: Message):
    """Игра в рулетку"""
    user_id = message.from_user.id
    if await is_banned(user_id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /roulette amount")
        return
    
    try:
        bet = int(args[1])
        stars = await get_user_stars(user_id)
        
        if bet < 10:
            await message.reply("❌ Минимальная ставка: 10 ⭐")
            return
        
        if bet > stars:
            await message.reply("❌ Недостаточно звезд!")
            return
        
        await spend_stars(user_id, bet)
        
        import random
        colors = ["🔴", "⚫", "🟢"]
        player_color = random.choice(colors)
        wheel_color = random.choice(colors)
        
        if player_color == wheel_color:
            multiplier = 5 if wheel_color == "🟢" else 4
            win = bet * multiplier
            await add_stars(user_id, win)
            await message.reply(
                f"🎯 Вы выбрали: {player_color}\n"
                f"🎯 Выпало: {wheel_color}\n\n"
                f"✅ Вы выиграли {win} ⭐!"
            )
        else:
            await message.reply(
                f"🎯 Вы выбрали: {player_color}\n"
                f"🎯 Выпало: {wheel_color}\n\n"
                f"❌ Вы проиграли {bet} ⭐"
            )
    except ValueError:
        await message.reply("❌ Неверный формат!")

# Приветствие при добавлении в чат
@dp.message(F.new_chat_members)
async def on_new_member(message: Message):
    """Обработчик добавления бота в чат"""
    for member in message.new_chat_members:
        if member.id == bot.id:
            await add_chat(message.chat.id, message.chat.type, message.chat.title)
            welcome_text = (
                f"🌟 Добро пожаловать в {GAME_NAME}!\n\n"
                f"Я игровой бот с фермами, NFT и казино!\n\n"
                f"Используйте команды:\n"
                f"/start - Начать игру\n"
                f"/help - Справка\n"
                f"/profile - Профиль\n"
                f"/casino - Казино"
            )
            await message.reply(welcome_text)

async def main():
    """Главная функция"""
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

