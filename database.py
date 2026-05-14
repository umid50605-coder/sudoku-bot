import sqlite3
import datetime
import json
import random
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_name="sudoku.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.insert_default_packages()
    
    def create_tables(self):
        """Barcha jadvallarni yaratish"""
        
        # Foydalanuvchilar
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date TEXT DEFAULT (datetime('now')),
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                best_time INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                referrer_id INTEGER,
                referal_count INTEGER DEFAULT 0,
                last_bonus_date TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT
            )
        """)
        
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
        except:
            pass
        
        # O'yinlar tarixi
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                difficulty TEXT,
                time_spent INTEGER,
                completed INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                played_date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Reklama ko'rishlar
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ad_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                viewed_date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Ochko operatsiyalari tarixi
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT,
                description TEXT,
                date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Ochko paketlari
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER,
                coins INTEGER,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Turnirlar
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                start_date TEXT,
                end_date TEXT,
                entry_fee INTEGER DEFAULT 0,
                prize_pool INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Turnir ishtirokchilari
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournament_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                user_id INTEGER,
                score INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                best_time INTEGER DEFAULT 0,
                joined_date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # ============ GURUH TURNIRI (YANGI) ============
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                creator_id INTEGER,
                name TEXT DEFAULT 'Guruh turniri',
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'waiting',
                difficulty TEXT DEFAULT 'medium',
                board TEXT,
                solution TEXT,
                max_players INTEGER DEFAULT 10,
                min_players INTEGER DEFAULT 2,
                prize_pool INTEGER DEFAULT 0,
                entry_fee INTEGER DEFAULT 0
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_tournament_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                user_id INTEGER,
                first_name TEXT,
                username TEXT,
                finish_time INTEGER,
                score INTEGER DEFAULT 0,
                place INTEGER,
                completed INTEGER DEFAULT 0,
                joined_date TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (tournament_id) REFERENCES group_tournaments (id)
            )
        """)
        
        self.conn.commit()
    
    # ========== FOYDALANUVCHILAR ==========
    def add_user(self, user_id: int, username: str, first_name: str, referrer_id: Optional[int] = None):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, referrer_id) VALUES (?, ?, ?, ?)",
                           (user_id, username, first_name, referrer_id))
        if referrer_id:
            self.cursor.execute("UPDATE users SET referal_count = referal_count + 1 WHERE user_id = ?", (referrer_id,))
            self.add_coins(referrer_id, 50, "referal", "Do'st taklif qilgani uchun bonus")
        self.conn.commit()
    
    def user_exists(self, user_id: int) -> bool:
        self.cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        self.cursor.execute("""SELECT user_id, username, first_name, total_games, total_wins, 
                   best_time, total_score, coins, referal_count, referrer_id, last_bonus_date, is_premium
                   FROM users WHERE user_id = ?""", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {"user_id": row[0], "username": row[1], "first_name": row[2], "total_games": row[3],
                    "total_wins": row[4], "best_time": row[5], "total_score": row[6], "coins": row[7],
                    "referal_count": row[8], "referrer_id": row[9], "last_bonus_date": row[10], "is_premium": row[11]}
        return None
    
    # ========== O'YINLAR ==========
    def save_game(self, user_id: int, difficulty: str, time_spent: int, completed: bool, score: int):
        self.cursor.execute("INSERT INTO games (user_id, difficulty, time_spent, completed, score) VALUES (?, ?, ?, ?, ?)",
                           (user_id, difficulty, time_spent, 1 if completed else 0, score))
        self.cursor.execute("UPDATE users SET total_games = total_games + 1, total_score = total_score + ? WHERE user_id = ?", (score, user_id))
        if completed:
            self.cursor.execute("UPDATE users SET total_wins = total_wins + 1 WHERE user_id = ?", (user_id,))
            if time_spent > 0:
                self.cursor.execute("UPDATE users SET best_time = CASE WHEN best_time = 0 THEN ? WHEN ? < best_time THEN ? ELSE best_time END WHERE user_id = ?",
                                   (time_spent, time_spent, time_spent, user_id))
            coins_map = {'easy': 10, 'medium': 20, 'hard': 30}
            self.add_coins(user_id, coins_map.get(difficulty, 10), "game_win", f"{difficulty} o'yin - G'alaba")
        self.conn.commit()
    
    # ========== REYTING ==========
    def get_top_players(self, limit: int = 10) -> List[Dict]:
        self.cursor.execute("""SELECT user_id, first_name, username, total_score, total_wins, total_games, best_time, coins
                   FROM users ORDER BY total_score DESC LIMIT ?""", (limit,))
        return [{"user_id": r[0], "first_name": r[1], "username": r[2], "total_score": r[3], "total_wins": r[4],
                 "total_games": r[5], "best_time": r[6], "coins": r[7]} for r in self.cursor.fetchall()]
    
    def get_today_top(self, limit: int = 10) -> List[Dict]:
        today = datetime.date.today().isoformat()
        self.cursor.execute("""SELECT u.user_id, u.first_name, u.username, COUNT(g.id), SUM(g.completed), SUM(g.score)
                   FROM users u JOIN games g ON u.user_id = g.user_id WHERE date(g.played_date) = ?
                   GROUP BY u.user_id ORDER BY SUM(g.score) DESC LIMIT ?""", (today, limit))
        return [{"user_id": r[0], "first_name": r[1], "username": r[2], "games_today": r[3],
                 "wins_today": r[4], "score_today": r[5]} for r in self.cursor.fetchall()]
    
    # ========== STATISTIKA ==========
    def get_user_stats(self, user_id: int) -> Dict:
        user = self.get_user(user_id) or {}
        today = datetime.date.today().isoformat()
        self.cursor.execute("SELECT COUNT(*), SUM(completed), SUM(score) FROM games WHERE user_id = ? AND date(played_date) = ?", (user_id, today))
        row = self.cursor.fetchone()
        self.cursor.execute("SELECT difficulty, COUNT(*) FROM games WHERE user_id = ? GROUP BY difficulty ORDER BY COUNT(*) DESC LIMIT 1", (user_id,))
        fav = self.cursor.fetchone()
        return {**user, "today_games": row[0] or 0, "today_wins": row[1] or 0, "today_score": row[2] or 0,
                "favorite_difficulty": fav[0] if fav else "medium"}
    
    # ========== KUNLIK BONUS ==========
    def can_claim_bonus(self, user_id: int) -> bool:
        self.cursor.execute("SELECT last_bonus_date FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row or not row[0]: return True
        return datetime.date.fromisoformat(row[0]) < datetime.date.today()
    
    def claim_bonus(self, user_id: int, bonus_score: int = 100):
        today = datetime.date.today().isoformat()
        self.cursor.execute("UPDATE users SET total_score = total_score + ?, last_bonus_date = ? WHERE user_id = ?", (bonus_score, today, user_id))
        self.add_coins(user_id, 15, "daily_bonus", "Kunlik bonus (+15)")
        self.conn.commit()
    
    # ========== OCHKO TIZIMI ==========
    def add_coins(self, user_id: int, amount: int, trans_type: str, description: str = ""):
        self.cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        self.cursor.execute("INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                           (user_id, amount, trans_type, description))
        self.conn.commit()
    
    def spend_coins(self, user_id: int, amount: int, trans_type: str, description: str = "") -> bool:
        self.cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row or row[0] < amount: return False
        self.cursor.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
        self.cursor.execute("INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                           (user_id, -amount, trans_type, description))
        self.conn.commit()
        return True
    
    def get_user_coins(self, user_id: int) -> int:
        self.cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0
    
    def get_coin_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        self.cursor.execute("SELECT amount, type, description, date FROM coin_transactions WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user_id, limit))
        return [{"amount": r[0], "type": r[1], "description": r[2], "date": r[3]} for r in self.cursor.fetchall()]
    
    def get_coin_packages(self) -> List[Dict]:
        self.cursor.execute("SELECT id, name, price, coins FROM coin_packages WHERE is_active = 1 ORDER BY price ASC")
        return [{"id": r[0], "name": r[1], "price": r[2], "coins": r[3]} for r in self.cursor.fetchall()]
    
    def insert_default_packages(self):
        self.cursor.execute("SELECT COUNT(*) FROM coin_packages")
        if self.cursor.fetchone()[0] == 0:
            for name, price, coins in [("Kichik paket", 5000, 100), ("O'rta paket", 10000, 250),
                                        ("Katta paket", 25000, 750), ("Mega paket", 50000, 2000)]:
                self.cursor.execute("INSERT INTO coin_packages (name, price, coins) VALUES (?, ?, ?)", (name, price, coins))
            self.conn.commit()
    
    # ========== REKLAMA ==========
    def get_ads_watched_today(self, user_id: int) -> int:
        today = datetime.date.today().isoformat()
        self.cursor.execute("SELECT COUNT(*) FROM ad_views WHERE user_id = ? AND date(viewed_date) = ?", (user_id, today))
        return self.cursor.fetchone()[0]
    
    def record_ad_view(self, user_id: int):
        self.cursor.execute("INSERT INTO ad_views (user_id) VALUES (?)", (user_id,))
        self.add_coins(user_id, 5, "ad_view", "Reklama ko'rish (+5)")
        self.conn.commit()
    
    # ========== UMUMIY STATISTIKA ==========
    def get_total_stats(self) -> Dict:
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM games")
        total_games = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM games WHERE completed = 1")
        total_wins = self.cursor.fetchone()[0]
        return {"total_users": total_users, "total_games": total_games, "total_wins": total_wins}
    
    # ========== KLASSIK TURNIRLAR ==========
    def create_tournament(self, name: str, tour_type: str, difficulty: str, duration_hours: int, entry_fee: int, prize_pool: int = 0) -> int:
        now = datetime.datetime.now()
        end = now + datetime.timedelta(hours=duration_hours)
        self.cursor.execute("INSERT INTO tournaments (name, type, start_date, end_date, entry_fee, prize_pool) VALUES (?, ?, ?, ?, ?, ?)",
                           (name, tour_type, now.isoformat(), end.isoformat(), entry_fee, prize_pool))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_active_tournaments(self) -> List[Dict]:
        now = datetime.datetime.now().isoformat()
        self.cursor.execute("SELECT id, name, type, start_date, end_date, entry_fee, prize_pool, status FROM tournaments WHERE status = 'active' AND end_date > ? ORDER BY entry_fee ASC", (now,))
        return [{"id": r[0], "name": r[1], "type": r[2], "start_date": r[3], "end_date": r[4],
                 "entry_fee": r[5], "prize_pool": r[6], "status": r[7]} for r in self.cursor.fetchall()]
    
    def get_tournament(self, tournament_id: int) -> Optional[Dict]:
        self.cursor.execute("SELECT id, name, type, start_date, end_date, entry_fee, prize_pool, status FROM tournaments WHERE id = ?", (tournament_id,))
        row = self.cursor.fetchone()
        return {"id": row[0], "name": row[1], "type": row[2], "start_date": row[3], "end_date": row[4],
                "entry_fee": row[5], "prize_pool": row[6], "status": row[7]} if row else None
    
    def join_tournament(self, tournament_id: int, user_id: int) -> str:
        tournament = self.get_tournament(tournament_id)
        if not tournament: return "not_found"
        self.cursor.execute("SELECT 1 FROM tournament_participants WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id))
        if self.cursor.fetchone(): return "already"
        if tournament['entry_fee'] > 0:
            if not self.spend_coins(user_id, tournament['entry_fee'], "tournament_entry", f"{tournament['name']} turniriga kirish"):
                return "no_coins"
        self.cursor.execute("INSERT INTO tournament_participants (tournament_id, user_id) VALUES (?, ?)", (tournament_id, user_id))
        self.cursor.execute("UPDATE tournaments SET prize_pool = prize_pool + ? WHERE id = ?", (tournament['entry_fee'], tournament_id))
        self.conn.commit()
        return "success"
    
    def get_tournament_players(self, tournament_id: int) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM tournament_participants WHERE tournament_id = ?", (tournament_id,))
        return self.cursor.fetchone()[0]
    
    def get_tournament_leaderboard(self, tournament_id: int, limit: int = 10) -> List[Dict]:
        self.cursor.execute("""SELECT u.first_name, u.username, tp.score, tp.games_played, tp.best_time
                   FROM tournament_participants tp JOIN users u ON tp.user_id = u.user_id
                   WHERE tp.tournament_id = ? ORDER BY tp.score DESC, tp.best_time ASC LIMIT ?""", (tournament_id, limit))
        return [{"first_name": r[0], "username": r[1], "score": r[2], "games_played": r[3], "best_time": r[4]} for r in self.cursor.fetchall()]
    
    def update_tournament_score(self, tournament_id: int, user_id: int, score: int, time_spent: int):
        self.cursor.execute("""UPDATE tournament_participants SET score = score + ?, games_played = games_played + 1,
                   best_time = CASE WHEN best_time = 0 THEN ? WHEN ? < best_time THEN ? ELSE best_time END
                   WHERE tournament_id = ? AND user_id = ?""",
                   (score, time_spent, time_spent, time_spent, tournament_id, user_id))
        self.conn.commit()
    
    def finish_tournament(self, tournament_id: int) -> bool:
        self.cursor.execute("UPDATE tournaments SET status = 'finished' WHERE id = ?", (tournament_id,))
        self.cursor.execute("SELECT tp.user_id, tp.score FROM tournament_participants tp WHERE tp.tournament_id = ? ORDER BY tp.score DESC LIMIT 3", (tournament_id,))
        winners = self.cursor.fetchall()
        if not winners:
            self.conn.commit()
            return False
        self.cursor.execute("SELECT prize_pool FROM tournaments WHERE id = ?", (tournament_id,))
        pool = self.cursor.fetchone()[0]
        percents = [0.50, 0.30, 0.20]
        for i, (winner_id, score) in enumerate(winners):
            if i < len(percents):
                prize = int(pool * percents[i])
                if prize > 0:
                    self.add_coins(winner_id, prize, "tournament_win", f"Turnir g'olibi ({i+1}-o'rin)")
        self.conn.commit()
        return True
    
    def get_user_tournaments(self, user_id: int) -> List[Dict]:
        self.cursor.execute("""SELECT t.id, t.name, t.type, t.end_date, t.status, tp.score, tp.games_played
                   FROM tournament_participants tp JOIN tournaments t ON tp.tournament_id = t.id
                   WHERE tp.user_id = ? ORDER BY t.end_date DESC""", (user_id,))
        return [{"id": r[0], "name": r[1], "type": r[2], "end_date": r[3], "status": r[4],
                 "score": r[5], "games_played": r[6]} for r in self.cursor.fetchall()]
    
    # ========== GURUH TURNIRI (YANGI) ==========
    def create_group_tournament(self, chat_id: int, creator_id: int, name: str, difficulty: str = "medium",
                                max_players: int = 10, entry_fee: int = 0) -> int:
        now = datetime.datetime.now()
        end = now + datetime.timedelta(hours=1)
        self.cursor.execute("""INSERT INTO group_tournaments (chat_id, creator_id, name, start_date, end_date,
                   difficulty, max_players, entry_fee) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (chat_id, creator_id, name, now.isoformat(), end.isoformat(), difficulty, max_players, entry_fee))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def join_group_tournament(self, tournament_id: int, user_id: int, first_name: str, username: str) -> str:
        self.cursor.execute("SELECT * FROM group_tournaments WHERE id = ? AND status = 'waiting'", (tournament_id,))
        if not self.cursor.fetchone(): return "not_found"
        self.cursor.execute("SELECT 1 FROM group_tournament_players WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id))
        if self.cursor.fetchone(): return "already"
        self.cursor.execute("SELECT entry_fee FROM group_tournaments WHERE id = ?", (tournament_id,))
        fee = self.cursor.fetchone()[0]
        if fee > 0:
            if not self.spend_coins(user_id, fee, "group_tournament_entry", "Guruh turniriga kirish"):
                return "no_coins"
        self.cursor.execute("INSERT INTO group_tournament_players (tournament_id, user_id, first_name, username) VALUES (?, ?, ?, ?)",
                           (tournament_id, user_id, first_name, username))
        self.conn.commit()
        return "success"
    
    def start_group_tournament(self, tournament_id: int, board: List, solution: List) -> bool:
        self.cursor.execute("""UPDATE group_tournaments SET status = 'active', board = ?, solution = ?
                   WHERE id = ? AND status = 'waiting'""", (json.dumps(board), json.dumps(solution), tournament_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_group_tournament(self, tournament_id: int) -> Optional[Dict]:
        self.cursor.execute("""SELECT id, chat_id, creator_id, name, start_date, end_date, status, difficulty,
                   board, solution, max_players, entry_fee, prize_pool FROM group_tournaments WHERE id = ?""", (tournament_id,))
        row = self.cursor.fetchone()
        if row:
            return {"id": row[0], "chat_id": row[1], "creator_id": row[2], "name": row[3], "start_date": row[4],
                    "end_date": row[5], "status": row[6], "difficulty": row[7], "board": json.loads(row[8]) if row[8] else None,
                    "solution": json.loads(row[9]) if row[9] else None, "max_players": row[10], "entry_fee": row[11], "prize_pool": row[12]}
        return None
    
    def get_group_tournament_players(self, tournament_id: int) -> List[Dict]:
        self.cursor.execute("""SELECT user_id, first_name, username, finish_time, score, place, completed
                   FROM group_tournament_players WHERE tournament_id = ? ORDER BY place ASC NULLS LAST, finish_time ASC""", (tournament_id,))
        return [{"user_id": r[0], "first_name": r[1], "username": r[2], "finish_time": r[3],
                 "score": r[4], "place": r[5], "completed": r[6]} for r in self.cursor.fetchall()]
    
    def finish_group_tournament_player(self, tournament_id: int, user_id: int, time_spent: int, score: int) -> int:
        """O'yinchi tugatganda. Qaytaradi: o'rin (1,2,3...)"""
        self.cursor.execute("SELECT COUNT(*) FROM group_tournament_players WHERE tournament_id = ? AND completed = 1", (tournament_id,))
        finished_count = self.cursor.fetchone()[0]
        place = finished_count + 1
        self.cursor.execute("""UPDATE group_tournament_players SET finish_time = ?, score = ?, place = ?, completed = 1
                   WHERE tournament_id = ? AND user_id = ?""", (time_spent, score, place, tournament_id, user_id))
        self.cursor.execute("UPDATE group_tournaments SET prize_pool = prize_pool + ? WHERE id = ?", (score // 2, tournament_id))
        self.conn.commit()
        return place
    
    def finish_group_tournament(self, tournament_id: int):
        """Guruh turnirini yakunlash va sovrinlarni tarqatish"""
        self.cursor.execute("UPDATE group_tournaments SET status = 'finished' WHERE id = ?", (tournament_id,))
        self.cursor.execute("SELECT user_id, place FROM group_tournament_players WHERE tournament_id = ? AND completed = 1 ORDER BY place ASC LIMIT 3", (tournament_id,))
        winners = self.cursor.fetchall()
        self.cursor.execute("SELECT prize_pool FROM group_tournaments WHERE id = ?", (tournament_id,))
        pool = self.cursor.fetchone()[0]
        prizes = {1: int(pool * 0.50), 2: int(pool * 0.30), 3: int(pool * 0.20)}
        for user_id, place in winners:
            if place in prizes and prizes[place] > 0:
                self.add_coins(user_id, prizes[place], "group_tournament_win", f"Guruh turniri {place}-o'rin")
        self.conn.commit()
    
    def count_group_tournament_players(self, tournament_id: int) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM group_tournament_players WHERE tournament_id = ?", (tournament_id,))
        return self.cursor.fetchone()[0]
    
    def is_user_in_group_tournament(self, tournament_id: int, user_id: int) -> bool:
        self.cursor.execute("SELECT 1 FROM group_tournament_players WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id))
        return self.cursor.fetchone() is not None
    
    def close(self):
        self.conn.close()

db = Database()