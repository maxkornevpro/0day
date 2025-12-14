import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8255377913:AAHAFPr1r5Hv1NH7qQ7xLByWuiwV_hyu6dc")

# Настройки игры
GAME_NAME = "0DAY FARM EMPIRE"
INITIAL_STARS = 200  # Начальное количество звезд
FARM_BASE_PRICE = 50  # Базовая цена фермы
FARM_BASE_INCOME = 5  # Базовый доход с фермы в час

# NFT подарки Telegram (их ID в Telegram)
NFT_GIFTS = {
    "snoop_dogg": {
        "name": "🎤 Snoop Dogg",
        "price": 5000,
        "boost": 1.5,  # +50% к доходу
        "gift_id": "snoop_dogg"
    },
    "lunar_snake": {
        "name": "🐍 Lunar Snake",
        "price": 3500,
        "boost": 1.3,  # +30% к доходу
        "gift_id": "lunar_snake"
    },
    "crystal_ball": {
        "name": "🔮 Crystal Ball",
        "price": 6000,
        "boost": 1.6,  # +60% к доходу
        "gift_id": "crystal_ball"
    },
    "golden_coin": {
        "name": "🪙 Golden Coin",
        "price": 3000,
        "boost": 1.25,  # +25% к доходу
        "gift_id": "golden_coin"
    },
    "diamond_ring": {
        "name": "💍 Diamond Ring",
        "price": 10000,
        "boost": 2.0,  # +100% к доходу
        "gift_id": "diamond_ring"
    },
    "magic_lamp": {
        "name": "🪔 Magic Lamp",
        "price": 7500,
        "boost": 1.7,  # +70% к доходу
        "gift_id": "magic_lamp"
    },
    "fire_dragon": {
        "name": "🐉 Fire Dragon",
        "price": 12000,
        "boost": 2.2,  # +120% к доходу
        "gift_id": "fire_dragon"
    },
    "cosmic_star": {
        "name": "⭐ Cosmic Star",
        "price": 8000,
        "boost": 1.8,  # +80% к доходу
        "gift_id": "cosmic_star"
    },
    "golden_crown": {
        "name": "👑 Golden Crown",
        "price": 15000,
        "boost": 2.5,  # +150% к доходу
        "gift_id": "golden_crown"
    },
    "mystic_orb": {
        "name": "🔮 Mystic Orb",
        "price": 9000,
        "boost": 1.9,  # +90% к доходу
        "gift_id": "mystic_orb"
    }
}

# Настройки реферальной системы
REFERRAL_REWARD = 100  # Награда за регистрацию по реферальной ссылке

# Типы ферм
FARM_TYPES = {
    "starter": {
        "name": "🌱 Стартовая ферма",
        "price": 200,
        "income_per_hour": 60
    },
    "basic": {
        "name": "🌾 Базовая ферма",
        "price": 500,
        "income_per_hour": 240
    },
    "advanced": {
        "name": "🚜 Продвинутая ферма",
        "price": 2000,
        "income_per_hour": 1200
    },
    "premium": {
        "name": "🏭 Премиум ферма",
        "price": 8000,
        "income_per_hour": 5400
    },
    "elite": {
        "name": "💎 Элитная ферма",
        "price": 25000,
        "income_per_hour": 18000
    },
    "legendary": {
        "name": "👑 Легендарная ферма",
        "price": 75000,
        "income_per_hour": 60000
    },
    "mythic": {
        "name": "🌟 Мифическая ферма",
        "price": 200000,
        "income_per_hour": 180000
    },
    "ultimate": {
        "name": "⚡ Ультимативная ферма",
        "price": 500000,
        "income_per_hour": 450000
    },
    "quantum": {
        "name": "⚛️ Квантовая ферма",
        "price": 1000000,
        "income_per_hour": 900000
    },
    "cosmic": {
        "name": "🌌 Космическая ферма",
        "price": 2500000,
        "income_per_hour": 2250000
    },
    "divine": {
        "name": "✨ Божественная ферма",
        "price": 5000000,
        "income_per_hour": 4500000
    },
    "infinity": {
        "name": "♾️ Бесконечная ферма",
        "price": 10000000,
        "income_per_hour": 9000000
    }
}

