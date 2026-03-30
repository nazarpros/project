import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect('dragon_game.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 100,
    last_dragon_search TEXT,
    current_dragon_id INTEGER DEFAULT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS dragons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    dragon_type TEXT,
    name TEXT,
    favorite_food TEXT,
    level INTEGER DEFAULT 1,
    health INTEGER DEFAULT 100,
    attack INTEGER DEFAULT 10,
    FOREIGN KEY (user_id) REFERENCES players (user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS raids (
    user_id INTEGER PRIMARY KEY,
    raid_active INTEGER DEFAULT 0,
    enemies_left INTEGER DEFAULT 0,
    raid_dragons INTEGER DEFAULT 0
)
''')

conn.commit()

# Словарь драконов
DRAGONS = {
    "Громмель": {
        "type": "Камнеед",
        "chance": 25,
        "health": 100,
        "attack": 15,
        "favorite_foods": ["камень", "рыба"],
        "gifs": {
            "found": "https://i.pinimg.com/originals/4a/5c/8d/4a5c8d8b8e8b8e8b8e8b8e8b8e8b8e8b.gif",
            "feed": "https://64.media.tumblr.com/9f9c8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_nyv7xqR6k51tpv8rao1_500.gif",
            "disgust": "https://i.pinimg.com/originals/4a/5c/8d/4a5c8d8b8e8b8e8b8e8b8e8b8e8b8e8b.gif"
        }
    },
    "Злобный Змеевик": {
        "type": "Ищейка",
        "chance": 25,
        "health": 90,
        "attack": 18,
        "favorite_foods": ["рыба", "курица"],
        "gifs": {
            "found": "https://64.media.tumblr.com/d0d1b8e8b8e8b8e8b8e8b8e8b8e8b8e8/tumblr_ojo9vfEfjv1vpniolo1_500.gif",
            "feed": "https://static.wikia.nocookie.net/httyd/images/9/90/Астрид_прощается_с_громгильдой.jpg/revision/latest/scale-to-width-down/250?cb=20140720094409&path-prefix=ru",
            "disgust": "https://64.media.tumblr.com/6f9f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_omg9uyqIrN1vpniolo1_500.gif"
        }
    },
    "Ужасное чудовище": {
        "type": "Кочегар",
        "chance": 25,
        "health": 110,
        "attack": 20,
        "favorite_foods": ["уголь", "камень"],
        "gifs": {
            "found": "https://64.media.tumblr.com/1f1f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_p0l5xrBq2W1tpv8rao1_500.gif",
            "feed": "https://i.makeagif.com/media/5-20-2015/8f8e8b.gif",
            "disgust": "https://64.media.tumblr.com/1f1f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_p0l5xrBq2W1tpv8rao1_500.gif"
        }
    },
    "Кошмарный пристеголов": {
        "type": "Грозящий",
        "chance": 25,
        "health": 85,
        "attack": 22,
        "favorite_foods": ["курица", "угорь"],
        "gifs": {
            "found": "https://64.media.tumblr.com/1f1f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_ngwgo8BIKt1tpv8rao1_500.gif",
            "feed": "https://64.media.tumblr.com/1f1f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_ngwgo8BIKt1tpv8rao1_500.gif",
            "disgust": "https://64.media.tumblr.com/2f2f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_ngwgo8BIKt1tpv8rao1_500.gif"
        }
    },
    "Ночная Фурия": {
        "type": "Разящий",
        "chance": 1,
        "health": 150,
        "attack": 35,
        "favorite_foods": ["рыба", "угорь"],
        "unique": True,
        "gifs": {
            "found": "https://i.pinimg.com/originals/c3/3f/8e/c33f8e8b8e8b8e8b8e8b8e8b8e8b8e8b.gif",
            "feed": "https://64.media.tumblr.com/b9f9f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_p0l5xrBq2W1tpv8rao1_500.gif",
            "tame": "https://64.media.tumblr.com/b8f8f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_p0l5xrBq2W1tpv8rao1_500.gif",
            "disgust": "https://64.media.tumblr.com/9f9f8e8b8e8b8e8b8e8b8e8b8e8b8e8b/tumblr_ngwgo8BIKt1tpv8rao1_500.gif"
        }
    }
}

def get_player(user_id, username):
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    
    if not player:
        cursor.execute('''
            INSERT INTO players (user_id, username, last_dragon_search)
            VALUES (?, ?, ?)
        ''', (user_id, username, (datetime.now() - timedelta(hours=3)).isoformat()))
        conn.commit()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
    
    return player

def update_player(user_id, gold=None):
    if gold is not None:
        cursor.execute("UPDATE players SET gold = ? WHERE user_id = ?", (gold, user_id))
        conn.commit()

def add_exp(user_id, amount):
    cursor.execute("SELECT level, exp FROM players WHERE user_id = ?", (user_id,))
    level, exp = cursor.fetchone()
    
    exp += amount
    level_up = False
    
    while exp >= level * 100:
        exp -= level * 100
        level += 1
        level_up = True
    
    cursor.execute("UPDATE players SET level = ?, exp = ? WHERE user_id = ?", (level, exp, user_id))
    conn.commit()
    
    return level_up, level, exp

def can_search_dragon(user_id):
    cursor.execute("SELECT last_dragon_search FROM players WHERE user_id = ?", (user_id,))
    last_search = cursor.fetchone()[0]
    
    last_time = datetime.fromisoformat(last_search)
    next_time = last_time + timedelta(hours=3)
    
    if datetime.now() >= next_time:
        return True, None
    else:
        wait_minutes = int((next_time - datetime.now()).total_seconds() / 60)
        return False, wait_minutes

def update_dragon_search_time(user_id):
    cursor.execute("UPDATE players SET last_dragon_search = ? WHERE user_id = ?", 
                   (datetime.now().isoformat(), user_id))
    conn.commit()

def search_dragon(user_id, level):
    base_chance = 10 + (level - 1) * 2
    chance = min(base_chance, 50)
    
    if random.randint(1, 100) <= chance:
        dragon_list = list(DRAGONS.keys())
        weights = [DRAGONS[d]["chance"] for d in dragon_list]
        
        dragon_name = random.choices(dragon_list, weights=weights)[0]
        dragon_data = DRAGONS[dragon_name]
        
        if dragon_name == "Ночная Фурия":
            cursor.execute("SELECT COUNT(*) FROM dragons WHERE dragon_type = ?", ("Ночная Фурия",))
            if cursor.fetchone()[0] >= 1:
                other_dragons = [d for d in dragon_list if d != "Ночная Фурия"]
                dragon_name = random.choice(other_dragons)
                dragon_data = DRAGONS[dragon_name]
        
        return True, dragon_name, dragon_data
    else:
        return False, None, None

def add_dragon(user_id, dragon_name, dragon_data, favorite_food=None):
    if dragon_name == "Ночная Фурия":
        cursor.execute("SELECT COUNT(*) FROM dragons WHERE dragon_type = ?", ("Ночная Фурия",))
        if cursor.fetchone()[0] >= 1:
            return None
    
    if not favorite_food:
        favorite_food = random.choice(dragon_data["favorite_foods"])
    
    cursor.execute('''
        INSERT INTO dragons (user_id, dragon_type, name, favorite_food, health, attack)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, dragon_data["type"], dragon_name, favorite_food, 
          dragon_data["health"], dragon_data["attack"]))
    conn.commit()
    return cursor.lastrowid

def get_player_dragons(user_id):
    cursor.execute("SELECT * FROM dragons WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def get_current_dragon(user_id):
    cursor.execute("SELECT current_dragon_id FROM players WHERE user_id = ?", (user_id,))
    current_id = cursor.fetchone()[0]
    
    if current_id:
        cursor.execute("SELECT * FROM dragons WHERE id = ?", (current_id,))
        return cursor.fetchone()
    return None

def set_current_dragon(user_id, dragon_id):
    cursor.execute("UPDATE players SET current_dragon_id = ? WHERE user_id = ?", (dragon_id, user_id))
    conn.commit()

def start_raid(user_id, dragon):
    enemies = random.randint(3, 8)
    cursor.execute('''
        INSERT OR REPLACE INTO raids (user_id, raid_active, enemies_left, raid_dragons)
        VALUES (?, 1, ?, 1)
    ''', (user_id, enemies))
    conn.commit()
    return enemies

def raid_attack(user_id):
    cursor.execute("SELECT enemies_left, raid_dragons FROM raids WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        return False, 0, 0
    
    enemies_left, dragons = result
    
    enemies_left -= 1
    
    if enemies_left <= 0:
        gold_reward = random.randint(50, 150)
        exp_reward = random.randint(20, 60)
        cursor.execute("DELETE FROM raids WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, gold_reward, exp_reward
    
    cursor.execute("UPDATE raids SET enemies_left = ? WHERE user_id = ?", (enemies_left, user_id))
    conn.commit()
    return False, enemies_left, 0

def get_raid_info(user_id):
    cursor.execute("SELECT enemies_left FROM raids WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return 0

def get_max_dragons(level):
    if level <= 10:
        return 1
    elif level <= 20:
        return 2
    elif level <= 30:
        return 3
    else:
        return 4
