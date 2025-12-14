import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_NAME = "game_bot.db"

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                stars INTEGER DEFAULT 200,
                last_collect TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица ферм
        await db.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                farm_type TEXT,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activated TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица NFT
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nft_type TEXT,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица рефералов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                reward_given BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id),
                UNIQUE(referred_id)
            )
        """)
        
        # Таблица аукционов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_type TEXT,
                starting_price INTEGER,
                current_bid INTEGER,
                current_bidder_id INTEGER,
                end_time TIMESTAMP,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_bidder_id) REFERENCES users (user_id)
            )
        """)
        
        await db.commit()

async def get_or_create_user(user_id: int) -> Dict:
    """Получить или создать пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = await cursor.fetchone()
        
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, stars, last_collect) VALUES (?, ?, ?)",
                (user_id, 200, datetime.now().isoformat())
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = await cursor.fetchone()
        
        return dict(user)

async def get_user_stars(user_id: int) -> int:
    """Получить количество звезд пользователя"""
    user = await get_or_create_user(user_id)
    return user['stars']

async def add_stars(user_id: int, amount: int):
    """Добавить звезды пользователю"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET stars = stars + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()

async def spend_stars(user_id: int, amount: int) -> bool:
    """Потратить звезды (возвращает True если успешно)"""
    current_stars = await get_user_stars(user_id)
    if current_stars >= amount:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE users SET stars = stars - ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()
        return True
    return False

async def buy_farm(user_id: int, farm_type: str) -> bool:
    """Купить ферму"""
    from config import FARM_TYPES
    
    if farm_type not in FARM_TYPES:
        return False
    
    price = FARM_TYPES[farm_type]["price"]
    
    if await spend_stars(user_id, price):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO farms (user_id, farm_type, last_activated, is_active) VALUES (?, ?, ?, 0)",
                (user_id, farm_type, datetime.now().isoformat())
            )
            await db.commit()
        return True
    return False

async def activate_farms(user_id: int) -> tuple[int, int]:
    """Активировать все фермы пользователя (возвращает (активировано, всего))"""
    farms = await get_user_farms(user_id)
    if not farms:
        return 0, 0
    
    activated_count = 0
    now = datetime.now()
    
    async with aiosqlite.connect(DB_NAME) as db:
        for farm in farms:
            farm_id = farm['id']
            last_activated = farm.get('last_activated')
            is_active = farm.get('is_active', 0)
            
            # Если ферма не активирована или прошло больше 6 часов
            can_activate = False
            if not last_activated or not is_active:
                can_activate = True
            else:
                last_activated_dt = datetime.fromisoformat(last_activated)
                hours_passed = (now - last_activated_dt).total_seconds() / 3600
                if hours_passed >= 6:
                    can_activate = True
            
            if can_activate:
                await db.execute(
                    "UPDATE farms SET last_activated = ?, is_active = 1 WHERE id = ?",
                    (now.isoformat(), farm_id)
                )
                activated_count += 1
        
        await db.commit()
    
    return activated_count, len(farms)

async def get_user_farms(user_id: int) -> List[Dict]:
    """Получить все фермы пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM farms WHERE user_id = ?",
            (user_id,)
        )
        farms = await cursor.fetchall()
        return [dict(farm) for farm in farms]

async def buy_nft(user_id: int, nft_type: str) -> bool:
    """Купить NFT"""
    from config import NFT_GIFTS
    
    if nft_type not in NFT_GIFTS:
        return False
    
    price = NFT_GIFTS[nft_type]["price"]
    
    if await spend_stars(user_id, price):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO nfts (user_id, nft_type) VALUES (?, ?)",
                (user_id, nft_type)
            )
            await db.commit()
        return True
    return False

async def get_user_nfts(user_id: int) -> List[Dict]:
    """Получить все NFT пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM nfts WHERE user_id = ?",
            (user_id,)
        )
        nfts = await cursor.fetchall()
        return [dict(nft) for nft in nfts]

async def calculate_total_boost(user_id: int) -> float:
    """Рассчитать общий буст от всех NFT"""
    from config import NFT_GIFTS
    
    nfts = await get_user_nfts(user_id)
    total_boost = 1.0
    
    for nft in nfts:
        nft_type = nft['nft_type']
        if nft_type in NFT_GIFTS:
            total_boost *= NFT_GIFTS[nft_type]["boost"]
    
    return total_boost

async def collect_farm_income(user_id: int) -> int:
    """Собрать доход с ферм (только с активированных ферм)"""
    from config import FARM_TYPES
    
    user = await get_or_create_user(user_id)
    farms = await get_user_farms(user_id)
    
    if not farms:
        return 0
    
    # Получаем время последнего сбора
    last_collect = datetime.fromisoformat(user['last_collect']) if user['last_collect'] else datetime.now()
    now = datetime.now()
    hours_passed = (now - last_collect).total_seconds() / 3600
    
    # Ограничиваем максимум 24 часа
    hours_passed = min(hours_passed, 24)
    
    # Рассчитываем базовый доход только с активированных ферм
    total_income = 0
    for farm in farms:
        # Проверяем, активирована ли ферма
        is_active = farm.get('is_active', 0)
        if not is_active:
            continue
        
        # Проверяем, не прошло ли 6 часов с активации
        last_activated = farm.get('last_activated')
        if last_activated:
            last_activated_dt = datetime.fromisoformat(last_activated)
            hours_since_activation = (now - last_activated_dt).total_seconds() / 3600
            if hours_since_activation >= 6:
                # Ферма деактивировалась
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute(
                        "UPDATE farms SET is_active = 0 WHERE id = ?",
                        (farm['id'],)
                    )
                    await db.commit()
                continue
        
        farm_type = farm['farm_type']
        if farm_type in FARM_TYPES:
            income_per_hour = FARM_TYPES[farm_type]["income_per_hour"]
            # Доход рассчитывается только за время с момента активации или последнего сбора
            if last_activated:
                last_activated_dt = datetime.fromisoformat(last_activated)
                collect_from = max(last_activated_dt, last_collect)
                hours_for_income = (now - collect_from).total_seconds() / 3600
                hours_for_income = min(hours_for_income, hours_passed)
            else:
                hours_for_income = hours_passed
            
            total_income += income_per_hour * hours_for_income
    
    # Применяем буст от NFT
    boost = await calculate_total_boost(user_id)
    total_income = int(total_income * boost)
    
    # Обновляем время последнего сбора
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_collect = ? WHERE user_id = ?",
            (now.isoformat(), user_id)
        )
        await db.commit()
    
    # Добавляем звезды
    if total_income > 0:
        await add_stars(user_id, total_income)
    
    return total_income

# Реферальная система
async def register_referral(referrer_id: int, referred_id: int) -> bool:
    """Зарегистрировать реферала (возвращает True если это новый реферал)"""
    if referrer_id == referred_id:
        return False
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, не регистрировался ли уже этот пользователь
        cursor = await db.execute(
            "SELECT * FROM referrals WHERE referred_id = ?",
            (referred_id,)
        )
        existing = await cursor.fetchone()
        
        if existing:
            return False
        
        # Регистрируем реферала
        await db.execute(
            "INSERT INTO referrals (referrer_id, referred_id, reward_given) VALUES (?, ?, 0)",
            (referrer_id, referred_id)
        )
        await db.commit()
        return True

async def give_referral_reward(referred_id: int) -> bool:
    """Выдать награду рефералу (возвращает True если награда была выдана)"""
    from config import REFERRAL_REWARD
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, была ли уже выдана награда
        cursor = await db.execute(
            "SELECT * FROM referrals WHERE referred_id = ? AND reward_given = 0",
            (referred_id,)
        )
        referral = await cursor.fetchone()
        
        if not referral:
            return False
        
        # Выдаем награду
        await add_stars(referred_id, REFERRAL_REWARD)
        
        # Отмечаем, что награда выдана
        await db.execute(
            "UPDATE referrals SET reward_given = 1 WHERE referred_id = ?",
            (referred_id,)
        )
        await db.commit()
        return True

async def get_referral_count(user_id: int) -> int:
    """Получить количество рефералов пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

# Система аукциона
async def create_auction(farm_type: str, starting_price: int, duration_hours: int = 24) -> int:
    """Создать аукцион (возвращает ID аукциона)"""
    from config import FARM_TYPES
    
    if farm_type not in FARM_TYPES:
        return 0
    
    end_time = datetime.now() + timedelta(hours=duration_hours)
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO auctions (farm_type, starting_price, current_bid, end_time, status) VALUES (?, ?, ?, ?, 'active')",
            (farm_type, starting_price, starting_price, end_time.isoformat())
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_auctions() -> List[Dict]:
    """Получить все активные аукционы"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE status = 'active' AND end_time > datetime('now') ORDER BY end_time ASC"
        )
        auctions = await cursor.fetchall()
        return [dict(auction) for auction in auctions]

async def place_bid(auction_id: int, user_id: int, bid_amount: int) -> tuple[bool, str]:
    """Сделать ставку на аукционе (возвращает (успех, сообщение))"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Получаем информацию об аукционе
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE id = ? AND status = 'active'",
            (auction_id,)
        )
        auction = await cursor.fetchone()
        
        if not auction:
            return False, "Аукцион не найден или уже завершен"
        
        auction_dict = dict(auction)
        
        # Проверяем, не истекло ли время
        end_time = datetime.fromisoformat(auction_dict['end_time'])
        if datetime.now() >= end_time:
            await db.execute(
                "UPDATE auctions SET status = 'ended' WHERE id = ?",
                (auction_id,)
            )
            await db.commit()
            return False, "Аукцион уже завершен"
        
        # Проверяем, что ставка больше текущей
        current_bid = auction_dict['current_bid']
        if bid_amount <= current_bid:
            return False, f"Ставка должна быть больше {current_bid} ⭐"
        
        # Проверяем баланс пользователя
        user_stars = await get_user_stars(user_id)
        if user_stars < bid_amount:
            return False, "Недостаточно звезд"
        
        # Возвращаем предыдущую ставку предыдущему участнику
        if auction_dict['current_bidder_id']:
            await add_stars(auction_dict['current_bidder_id'], auction_dict['current_bid'])
        
        # Списываем новую ставку
        await spend_stars(user_id, bid_amount)
        
        # Обновляем аукцион
        await db.execute(
            "UPDATE auctions SET current_bid = ?, current_bidder_id = ? WHERE id = ?",
            (bid_amount, user_id, auction_id)
        )
        await db.commit()
        
        return True, f"Ставка принята: {bid_amount} ⭐"

async def end_auction(auction_id: int) -> Optional[Dict]:
    """Завершить аукцион и выдать ферму победителю (возвращает информацию об аукционе)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE id = ?",
            (auction_id,)
        )
        auction = await cursor.fetchone()
        
        if not auction:
            return None
        
        auction_dict = dict(auction)
        
        if auction_dict['status'] != 'active':
            return None
        
        # Обновляем статус
        await db.execute(
            "UPDATE auctions SET status = 'ended' WHERE id = ?",
            (auction_id,)
        )
        await db.commit()
        
        # Если есть победитель, выдаем ему ферму
        if auction_dict['current_bidder_id']:
            winner_id = auction_dict['current_bidder_id']
            farm_type = auction_dict['farm_type']
            
            # Добавляем ферму победителю
            await db.execute(
                "INSERT INTO farms (user_id, farm_type) VALUES (?, ?)",
                (winner_id, farm_type)
            )
            await db.commit()
        
        return auction_dict

