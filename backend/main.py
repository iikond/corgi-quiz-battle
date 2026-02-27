from symtable import Symbol
from tokenize import String
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import random
import string
import json
import time
from gigachat import GigaChat

def generate_pin(length=6):
    symbols = string.ascii_uppercase + string.digits
    while True:
        pin = ''.join(random.choice(symbols) for _ in range(length))
        if pin not in games:
            return pin

# Конфигурация GigaChat
GIGACHAT_TOKEN = "MDE5Y2EwNzgtYzkwYS03ODFhLWE5MjItNTg1MmFlMWM5ZDY3OmE3Zjk3MTA0LThmMmEtNGM4My1iYjc0LTQ1YTMxN2ZjNDliNQ=="
USE_AI = True  # флаг для отладки

# Инициализация GigaChat
try:
    giga = GigaChat(credentials=GIGACHAT_TOKEN, model="GigaChat-2" ,verify_ssl_certs=False)
    print("✅ GigaChat подключён")
except Exception as e:
    print(f"❌ Ошибка подключения GigaChat: {e}")
    USE_AI = False
    giga = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'frontend/templates'),
    static_folder=os.path.join(BASE_DIR, 'frontend/static'),
)
socketio = SocketIO(app)

games = {}

# Запасные вопросы (если AI не работает)
FALLBACK_QUESTIONS = [
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

def generate_questions_with_ai(theme, num_questions):
    """Генерация вопросов через GigaChat с продвинутым парсингом"""
    if not USE_AI or not giga:
        print("AI недоступен, использую запасные вопросы")
        return FALLBACK_QUESTIONS[:num_questions]
    
    # разные варианты промпта (иногда AI лучше реагирует на краткость)
    prompts = [
        f"""Сгенерируй {num_questions} вопросов для викторины на тему "{theme}". 
        Верни ТОЛЬКО JSON массив без пояснений.
        Формат: [{{"text": "вопрос", "options": ["a","b","c","d"], "correct_index": 0}}]""",
        
        f"""Напиши {num_questions} вопросов на тему "{theme}" в формате JSON.
        Каждый вопрос: text, options (4 варианта), correct_index (0-3).
        Только JSON, ничего лишнего."""
    ]
    
    import re
    import json
    import time
    
    for attempt, prompt in enumerate(prompts):
        try:
            print(f"Попытка {attempt + 1} генерации {num_questions} вопросов...")
            response = giga.chat(prompt)
            text = response.choices[0].message.content
            
            # ========== ЖЁСТКИЙ ПАРСИНГ JSON ==========
            
            # Способ 1: пытаемся найти [ ... ]
            match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    questions = json.loads(json_str)
                    print(f"Найдено {len(questions)} вопросов через regex")
                    return validate_questions(questions, num_questions)
                except:
                    pass
            
            # Способ 2: берём всё от [ до ]
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                # чистим от мусора
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                try:
                    questions = json.loads(json_str)
                    print(f"Найдено {len(questions)} вопросов через срезы")
                    return validate_questions(questions, num_questions)
                except:
                    pass
            
            # Способ 3: ищем отдельные объекты { ... }
            objects = re.findall(r'\{[^{}]*\}', text)
            if objects:
                questions = []
                for obj_str in objects:
                    try:
                        q = json.loads(obj_str)
                        if all(k in q for k in ['text', 'options', 'correct_index']):
                            questions.append(q)
                    except:
                        continue
                if questions:
                    print(f"Найдено {len(questions)} вопросов через объекты")
                    return validate_questions(questions, num_questions)
            
            print(f"AI вернул невалидный JSON, пробуем другой промпт")
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка при генерации: {e}")
            time.sleep(2)
    
    print("Все попытки провалились, использую запасные вопросы")
    return FALLBACK_QUESTIONS[:num_questions]

def validate_questions(questions, expected_count):
    """Проверяет, что вопросы в правильном формате"""
    valid_questions = []
    for q in questions[:expected_count]:
        if (q.get("text") and 
            isinstance(q.get("options"), list) and 
            len(q.get("options", [])) == 4 and
            isinstance(q.get("correct_index"), int) and
            0 <= q["correct_index"] < 4):
            valid_questions.append(q)
    
    # Если валидных вопросов太少, добираем из запасных
    while len(valid_questions) < expected_count:
        idx = len(valid_questions) % len(FALLBACK_QUESTIONS)
        valid_questions.append(FALLBACK_QUESTIONS[idx])
    
    return valid_questions

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

    if not name or pin not in games:
        emit('error', {'message': 'Игра не найдена'})
        return

    game = games[pin]

    if name not in game['players']:
        game['players'].append(name)

        team_a = game['teams']['A']
        team_b = game['teams']['B']

        if len(team_a) <= len(team_b):
            team_a.append(name)
        else:
            team_b.append(name)

    emit('game_data', game, broadcast=True)

@socketio.on('create_game')
def handle_create_game(data):
    theme = data.get('theme', '').strip()
    raw_q_num = (data.get('q_num') or '').strip()

    try:
        q_num = int(raw_q_num)
    except ValueError:
        q_num = 5

    # Генерируем вопросы через AI (или берём запасные)
    raw_questions = generate_questions_with_ai(theme, q_num)
    questions = validate_questions(raw_questions, q_num)

    pin = generate_pin()
    games[pin] = {
        "pin": pin,
        "host_sid": request.sid,
        "theme": theme,
        "num_questions": q_num,
        "state": "lobby",
        "players": [],
        "teams": {"A": [], "B": []},
        "scores": {"A": 0, "B": 0},
        "current_team": "A",
        "current_question_index": 0,
        "questions": questions,
        "ai_generated": len(raw_questions) == q_num and USE_AI  # флаг для презентации
    }
    
    print(f"🎮 Игра {pin} создана, {len(questions)} вопросов")
    emit('game_created', {"pin": pin, "ai_generated": games[pin]["ai_generated"]}, to=request.sid)

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
            "ai_generated": game.get("ai_generated", False),
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

    try:
        choice_index = int(choice)
    except (TypeError, ValueError):
        return

    idx = game["current_question_index"]
    if idx >= len(game["questions"]):
        return

    q = game["questions"][idx]

    if choice_index == q["correct_index"]:
        game["scores"][team] += 1
        print(f"✅ Команда {team} ответила правильно! Счёт: A:{game['scores']['A']} B:{game['scores']['B']}")

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
        print(f"🏁 Игра {pin} завершена")
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
            "ai_generated": game.get("ai_generated", False),
        },
        broadcast=True,
    )

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')