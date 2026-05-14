from flask import Flask, render_template, jsonify, request
import random
import time
import sqlite3
import threading
import os
from database import db

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# ============ SUDOKU GENERATOR ============
class SudokuGenerator:
    def __init__(self):
        self.board = [[0]*9 for _ in range(9)]
        self.solution = [[0]*9 for _ in range(9)]
    
    def generate(self, difficulty='medium'):
        self.board = [[0]*9 for _ in range(9)]
        self._fill_diagonal()
        self._solve()
        self.solution = [row[:] for row in self.board]
        
        levels = {'easy': 35, 'medium': 45, 'hard': 55}
        remove = levels.get(difficulty, 45)
        
        positions = [(i, j) for i in range(9) for j in range(9)]
        random.shuffle(positions)
        
        for i, j in positions[:remove]:
            self.board[i][j] = 0
        
        return self.board, self.solution
    
    def _fill_diagonal(self):
        for box in range(0, 9, 3):
            self._fill_box(box, box)
    
    def _fill_box(self, row_start, col_start):
        nums = list(range(1, 10))
        random.shuffle(nums)
        for i in range(3):
            for j in range(3):
                self.board[row_start+i][col_start+j] = nums[i*3+j]
    
    def _solve(self):
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0:
                    for num in range(1, 10):
                        if self._is_safe(i, j, num):
                            self.board[i][j] = num
                            if self._solve():
                                return True
                            self.board[i][j] = 0
                    return False
        return True
    
    def _is_safe(self, row, col, num):
        for x in range(9):
            if self.board[row][x] == num or self.board[x][col] == num:
                return False
        start_row, start_col = 3*(row//3), 3*(col//3)
        for i in range(3):
            for j in range(3):
                if self.board[start_row+i][start_col+j] == num:
                    return False
        return True

generator = SudokuGenerator()

# ============ ASOSIY SAHIFALAR ============
@app.route('/')
def index():
    return render_template('game.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

# ============ GAME API ============
@app.route('/api/new-game')
def new_game():
    difficulty = request.args.get('difficulty', 'medium')
    board, solution = generator.generate(difficulty)
    return jsonify({'board': board, 'solution': solution, 'difficulty': difficulty})

@app.route('/api/save-game', methods=['POST'])
def save_game():
    data = request.json
    user_id = data['user_id']
    difficulty = data['difficulty']
    time_spent = int(data['time_spent'])
    completed = data['completed']
    score = data['score']
    
    if not db.user_exists(user_id):
        db.add_user(user_id, data.get('username', ''), data.get('first_name', ''))
    
    db.save_game(user_id, difficulty, time_spent, completed, score)
    return jsonify({'success': True})

# ============ STATS API ============
@app.route('/api/stats/<int:user_id>')
def get_stats(user_id):
    stats = db.get_user_stats(user_id)
    return jsonify(stats)

@app.route('/api/top')
def get_top():
    top = db.get_top_players(10)
    return jsonify(top)

@app.route('/api/total-stats')
def get_total_stats():
    return jsonify(db.get_total_stats())

# ============ OCHKO TIZIMI API ============
@app.route('/api/coins/<int:user_id>')
def get_coins(user_id):
    coins = db.get_user_coins(user_id)
    history = db.get_coin_history(user_id, 10)
    return jsonify({'coins': coins, 'history': history})

@app.route('/api/coin-packages')
def get_coin_packages():
    packages = db.get_coin_packages()
    return jsonify(packages)

@app.route('/api/claim-daily-bonus', methods=['POST'])
def claim_daily_bonus():
    data = request.json
    user_id = data['user_id']
    if db.can_claim_bonus(user_id):
        db.claim_bonus(user_id, 100)
        return jsonify({'success': True, 'coins': 15})
    return jsonify({'success': False})

@app.route('/api/spend-coins', methods=['POST'])
def spend_coins():
    data = request.json
    success = db.spend_coins(data['user_id'], data['amount'], data['type'], data.get('description', ''))
    return jsonify({'success': success})

@app.route('/api/ad-view', methods=['POST'])
def ad_view():
    data = request.json
    db.record_ad_view(data['user_id'])
    return jsonify({'success': True, 'coins': 5})

@app.route('/api/duel-bot', methods=['POST'])
def duel_bot():
    data = request.json
    result = db.duel_bot(data['user_id'])
    return jsonify(result)

# ============ TURNIR API ============
@app.route('/api/tournaments')
def get_tournaments():
    tournaments = db.get_active_tournaments()
    return jsonify(tournaments)

@app.route('/api/tournament/<int:tournament_id>')
def get_tournament(tournament_id):
    tournament = db.get_tournament(tournament_id)
    if tournament:
        tournament['players'] = db.get_tournament_players(tournament_id)
        tournament['leaderboard'] = db.get_tournament_leaderboard(tournament_id, 10)
    return jsonify(tournament or {})

@app.route('/api/tournament/<int:tournament_id>/join', methods=['POST'])
def join_tournament(tournament_id):
    data = request.json
    result = db.join_tournament(tournament_id, data['user_id'])
    messages = {'success': 'Qoshildingiz!', 'already': 'Allaqachon qoshilgansiz!', 'no_coins': 'Tanga yetarli emas!', 'not_found': 'Turnir topilmadi!'}
    return jsonify({'result': result, 'message': messages.get(result, 'Xatolik')})

@app.route('/api/tournament/<int:tournament_id>/leaderboard')
def tournament_leaderboard(tournament_id):
    return jsonify(db.get_tournament_leaderboard(tournament_id))

@app.route('/api/tournament/<int:tournament_id>/finish', methods=['POST'])
def finish_one_tournament(tournament_id):
    db.finish_tournament(tournament_id)
    return jsonify({'success': True})

@app.route('/api/tournament/finish-all', methods=['POST'])
def finish_all_tournaments():
    tournaments = db.get_active_tournaments()
    for t in tournaments:
        db.finish_tournament(t['id'])
    return jsonify({'success': True})

@app.route('/api/my-tournaments/<int:user_id>')
def my_tournaments(user_id):
    return jsonify(db.get_user_tournaments(user_id))

@app.route('/api/tournament/quick', methods=['POST'])
def create_quick_tournament():
    tid = db.create_tournament('⚡ Quick', 'quick', 'medium', 1, 25, 0)
    return jsonify({'success': True, 'id': tid})

@app.route('/api/tournament/daily', methods=['POST'])
def create_daily_tournament():
    tid = db.create_tournament('📅 Daily', 'daily', 'hard', 24, 100, 0)
    return jsonify({'success': True, 'id': tid})

# ============ ADMIN API ============
@app.route('/api/admin/add-coins', methods=['POST'])
def admin_add_coins():
    data = request.json
    db.add_coins(data['user_id'], data['coins'], 'admin', 'Admin qoshdi')
    return jsonify({'success': True})

@app.route('/api/admin/reset-coins', methods=['POST'])
def admin_reset_coins():
    data = request.json
    coins = db.get_user_coins(data['user_id'])
    if coins > 0:
        db.spend_coins(data['user_id'], coins, 'admin', 'Reset')
    return jsonify({'success': True})

@app.route('/api/admin/bonus-all', methods=['POST'])
def admin_bonus_all():
    conn = sqlite3.connect('sudoku.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + 50")
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============ GURUH TURNIRI API ============
@app.route('/api/group-tournament/create', methods=['POST'])
def create_group_tournament():
    data = request.json
    tid = db.create_group_tournament(data['chat_id'], data['creator_id'], data.get('name', 'Turnir'), data.get('difficulty', 'medium'), data.get('max_players', 10), data.get('entry_fee', 0))
    board, solution = generator.generate(data.get('difficulty', 'medium'))
    db.start_group_tournament(tid, board, solution)
    return jsonify({'success': True, 'tournament_id': tid, 'board': board})

@app.route('/api/group-tournament/<int:tid>/join', methods=['POST'])
def join_group_tournament(tid):
    data = request.json
    result = db.join_group_tournament(tid, data['user_id'], data.get('first_name', ''), data.get('username', ''))
    return jsonify({'result': result})

@app.route('/api/group-tournament/<int:tid>')
def get_group_tournament(tid):
    tournament = db.get_group_tournament(tid)
    if tournament:
        tournament['players'] = db.get_group_tournament_players(tid)
        tournament['count'] = db.count_group_tournament_players(tid)
    return jsonify(tournament or {})

# ============ ISHGA TUSHIRISH ============
# Botni darhol ishga tushirish (gunicorn uchun)
def run_bot():
    import bot
    bot.main()

# Botni alohida threadda ishga tushirish
import threading
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()
print("🤖 Bot thread ishga tushdi!")

# Flask sozlamalari
port = int(os.environ.get("PORT", 5000))
print(f"🚀 Flask server ishga tushmoqda... Port: {port}")

# Eski if __name__ qismini o'chiramiz