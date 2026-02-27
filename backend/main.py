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

QUESTION_BANK = [
    {
        "text": "Какая технология чаще всего ассоциируется со скоростью и динамикой?",
        "options": ["Блокчейн", "Искусственный интеллект", "Квантовые компьютеры", "Облачные хранилища"],
        "correct_index": 1,
    },
    {
        "text": "Какой цвет чаще всего используют для обозначения опасной зоны на тахометре?",
        "options": ["Зелёный", "Синий", "Красный", "Жёлтый"],
        "correct_index": 2,
    },
    {
        "text": "Какую из этих технологий чаще всего используют в онлайн‑играх для общения игроков?",
        "options": ["WebSockets", "FTP", "SMTP", "SSH"],
        "correct_index": 0,
    },
]

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
    name = data.get('name', '').strip()
    pin = (data.get('pin') or '').strip().upper()

    # защита от мусора
    if not name or pin not in games:
        # потом можно послать emit с ошибкой
        return

    game = games[pin]

    # если такого игрока ещё нет, добавляем
    if name not in game['players']:
        game['players'].append(name)

        team_a = game['teams']['A']
        team_b = game['teams']['B']

        # простое распределение: балансируем по количеству
        if len(team_a) <= len(team_b):
            team_a.append(name)
        else:
            team_b.append(name)

    # шлём актуальное состояние игры всем участникам
    emit('game_data', game, broadcast=True)

@socketio.on('create_game')
def handle_create_game(data):
    theme = data.get('theme', '').strip()
    raw_q_num = (data.get('q_num') or '').strip()

    try:
        q_num = int(raw_q_num)
    except ValueError:
        q_num = 5

    # простые вопросы-заглушки для прототипа
    questions = QUESTION_BANK[:q_num] if QUESTION_BANK else []

    pin = generate_pin()
    games[pin] = {
        "pin": pin,
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
        "questions": questions,    # список вопросов
    }
    emit('game_created', {"pin": pin}, to=request.sid)

@socketio.on('start_game')
def handle_start_game(data):
    pin = (data.get('pin') or '').strip().upper()
    if pin not in games:
        return

    game = games[pin]

    if not game["questions"]:
        return

    game["state"] = "playing"
    game["current_team"] = "A"
    game["current_question_index"] = 0

    q = game["questions"][game["current_question_index"]]

    emit(
        "question",
        {
            "pin": pin,
            "theme": game["theme"],
            "text": q["text"],
            "options": q["options"],
            "current_team": game["current_team"],
            "scores": game["scores"],
            "question_index": game["current_question_index"],
            "total_questions": len(game["questions"]),
            "time_limit": 30,
        },
        broadcast=True,
    )

@socketio.on('answer')
def handle_answer(data):
    pin = (data.get('pin') or '').strip().upper()
    team = data.get('team')
    choice = data.get('choice')

    if pin not in games or team not in ('A', 'B'):
        return

    game = games[pin]

    # преобразуем choice к int
    try:
        choice_index = int(choice)
    except (TypeError, ValueError):
        return

    idx = game["current_question_index"]
    if idx >= len(game["questions"]):
        return

    q = game["questions"][idx]

    # проверяем ответ
    if choice_index == q["correct_index"]:
        game["scores"][team] += 1

    # следующий вопрос и смена команды
    game["current_question_index"] += 1
    game["current_team"] = "B" if game["current_team"] == "A" else "A"

    if game["current_question_index"] >= len(game["questions"]):
        game["state"] = "finished"
        emit(
            "game_finished",
            {
                "pin": pin,
                "scores": game["scores"],
            },
            broadcast=True,
        )
        return

    next_q = game["questions"][game["current_question_index"]]

    emit(
        "question",
        {
            "pin": pin,
            "theme": game["theme"],
            "text": next_q["text"],
            "options": next_q["options"],
            "current_team": game["current_team"],
            "scores": game["scores"],
            "question_index": game["current_question_index"],
            "total_questions": len(game["questions"]),
            "time_limit": 30,
        },
        broadcast=True,
    )

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')