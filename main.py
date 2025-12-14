import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from config import BOT_TOKEN, FARM_TYPES, NFT_GIFTS, GAME_NAME
from database import (
    init_db, get_or_create_user, get_user_stars, 
    buy_farm, get_user_farms, buy_nft, get_user_nfts,
    calculate_total_boost, collect_farm_income,
    register_referral, give_referral_reward, get_referral_count,
    create_auction, get_active_auctions, place_bid, end_auction,
    activate_farms
)
from keyboards import (
    get_main_menu, get_farm_shop_keyboard, 
    get_nft_shop_keyboard, get_back_keyboard, get_auction_keyboard
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
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Проверяем реферальную ссылку
    is_new_user = False
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id:
                is_new_user = await register_referral(referrer_id, user_id)
                if is_new_user:
                    await give_referral_reward(user_id)
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

