from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import random
import string
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'dbname': 'tictactoe_db',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create games table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            code VARCHAR(10) UNIQUE NOT NULL,
            player1_email VARCHAR(255) NOT NULL,
            player2_email VARCHAR(255),
            board TEXT NOT NULL,
            move_history TEXT NOT NULL,
            current_turn VARCHAR(1) NOT NULL,
            winner VARCHAR(1),
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (email, password) VALUES (%s, %s)', (email, password))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'User created', 'email': email}), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'User already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user:
            return jsonify({'message': 'Login successful', 'email': email}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/create', methods=['POST'])
def create_game():
    data = request.json
    email = data.get('email')
    
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    board = json.dumps([None] * 9)
    move_history = json.dumps([])
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO games (code, player1_email, board, move_history, current_turn, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        ''', (code, email, board, move_history, 'X', 'waiting'))
        game = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        game['board'] = json.loads(game['board'])
        game['move_history'] = json.loads(game['move_history'])
        
        return jsonify(game), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/join', methods=['POST'])
def join_game():
    data = request.json
    code = data.get('code')
    email = data.get('email')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM games WHERE code = %s', (code,))
        game = cur.fetchone()
        
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        if game['player2_email']:
            return jsonify({'error': 'Game is full'}), 400
        
        if game['player1_email'] == email:
            return jsonify({'error': 'Cannot join your own game'}), 400
        
        cur.execute('''
            UPDATE games SET player2_email = %s, status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE code = %s
            RETURNING *
        ''', (email, 'playing', code))
        
        game = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        game['board'] = json.loads(game['board'])
        game['move_history'] = json.loads(game['move_history'])
        
        return jsonify(game), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/<code>', methods=['GET'])
def get_game(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM games WHERE code = %s', (code,))
        game = cur.fetchone()
        cur.close()
        conn.close()
        
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        game['board'] = json.loads(game['board'])
        game['move_history'] = json.loads(game['move_history'])
        
        return jsonify(game), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/move', methods=['POST'])
def make_move():
    data = request.json
    code = data.get('code')
    email = data.get('email')
    position = data.get('position')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM games WHERE code = %s', (code,))
        game = cur.fetchone()
        
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        board = json.loads(game['board'])
        move_history = json.loads(game['move_history'])
        
        # Determine player symbol
        if email == game['player1_email']:
            symbol = 'X'
        elif email == game['player2_email']:
            symbol = 'O'
        else:
            return jsonify({'error': 'Not a player in this game'}), 403
        
        # Check if it's player's turn
        if game['current_turn'] != symbol:
            return jsonify({'error': 'Not your turn'}), 400
        
        # Check if position is valid
        if board[position] is not None:
            return jsonify({'error': 'Position already occupied'}), 400
        
        # Make the move
        board[position] = symbol
        move_history.append({'position': position, 'symbol': symbol})
        
        # Remove oldest move if more than 6
        if len(move_history) > 6:
            oldest = move_history.pop(0)
            board[oldest['position']] = None
        
        # Check for winner
        winner = check_winner(board)
        
        # Update turn
        next_turn = 'O' if symbol == 'X' else 'X'
        
        cur.execute('''
            UPDATE games 
            SET board = %s, move_history = %s, current_turn = %s, winner = %s, updated_at = CURRENT_TIMESTAMP
            WHERE code = %s
            RETURNING *
        ''', (json.dumps(board), json.dumps(move_history), next_turn, winner, code))
        
        game = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        game['board'] = json.loads(game['board'])
        game['move_history'] = json.loads(game['move_history'])
        
        return jsonify(game), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_winner(board):
    lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    
    for line in lines:
        a, b, c = line
        if board[a] and board[a] == board[b] and board[a] == board[c]:
            return board[a]
    
    return None

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)