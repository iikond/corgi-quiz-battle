from symtable import Symbol
from tokenize import String
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import random
import string

def generate_pin(length=6):
    symbols = string.ascii_uppercase + string.digits  # A-Z и 0-9
    while True:
        pin = ''.join(random.choice(symbols) for _ in range(length))
        if pin not in games:  # чтобы PIN был уникальным среди активных игр
            return pin


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'frontend/templates'),
    static_folder=os.path.join(BASE_DIR, 'frontend/static'),
)
socketio = SocketIO(app)

games = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lobby')
def lobby():
    return render_template('lobby.html')

@app.route('/game')
def game():
    return render_template('game.html')

@socketio.on('connect')
def handle_connect():
    print('Клиент подключился')

@socketio.on('join_game')
def handle_join(data):
    pin = data['pin']
    if pin in games:
        emit('game_data', games[pin])

@socketio.on('create_game')
def handle_create_game(data):
    theme = data.get('theme', '').strip()
    raw_q_num = (data.get('q_num') or '').strip()

    try:
        q_num = int(raw_q_num)
    except ValueError:
        q_num = 5 

    pin = generate_pin()
    games[pin] = {
        "host_sid": request.sid,           # кто создал игру (id сокета)
        "theme": theme,            # тема вопросов
        "num_questions": q_num,        # сколько вопросов на команду
        "state": "lobby",          # "lobby" / "playing" / "finished"
        "players": [],             # список игроков
        "teams": {                 # две команды
            "A": [],
            "B": [],
        },
        "scores": {                # очки
            "A": 0,
            "B": 0,
        },
        "current_team": "A",       # чья сейчас очередь
        "current_question_index": 0,
        "questions": [],           # список вопросов (позже набьём руками)
    }
    emit('game_created', {"pin": pin}, to=request.sid)

@socketio.on('answer')
def handle_answer(data):
    name = data['name']
    pin = data['pin']
    emit('update_scores', games[pin]['scores'], broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')