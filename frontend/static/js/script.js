const socket = io(); // подключаемся к Flask-SocketIO
let currentPin = null;

// привязка кнопок
document.getElementById('enter_game').onclick = enter_game;
document.getElementById('start_game').onclick = create;

function enter_game() {
    join();
}

function join() {
    const name = document.getElementById('player_name').value.trim();
    const pin = document.getElementById('pin').value.trim(); // id из index.html

    if (!name || !pin) {
        alert('Введи имя и PIN');
        return;
    }

    socket.emit('join_game', { name, pin });
}

function create() {
    const theme = document.getElementById('host_theme').value.trim();
    const q_num = document.getElementById('host_num_questions').value.trim();

    if (!theme || !q_num) {
        alert('Укажи тему и количество вопросов');
        return;
    }

    socket.emit('create_game', { theme, q_num });
}

// лог для отладки
socket.on('connect', () => {
    console.log('Socket.IO подключён, id =', socket.id);
});

function renderLobbyPreview(game) {
    const box = document.getElementById('lobby_preview');
    if (!box) return;

    const teamA = (game.teams && game.teams.A) || [];
    const teamB = (game.teams && game.teams.B) || [];

    // запоминаем текущую игру
    currentPin = game.pin || currentPin;

    box.style.display = 'block';
    const isHost = game.host_sid && game.host_sid === socket.id;

    box.innerHTML = `
        <h2 class="lobby-title">Лобби игры (PIN ${game.pin || ''})</h2>
        <p class="lobby-status">Тема: ${game.theme || '—'} · Вопросов на команду: ${game.num_questions || '—'}</p>
        <div class="teams-wrapper">
            <div class="team-card team-a">
                <h3>Команда A</h3>
                <ul class="player-list">
                    ${teamA.length ? teamA.map(n => `<li>${n}</li>`).join('') : '<li>Ожидаем игроков…</li>'}
                </ul>
            </div>
            <div class="team-card team-b">
                <h3>Команда B</h3>
                <ul class="player-list">
                    ${teamB.length ? teamB.map(n => `<li>${n}</li>`).join('') : '<li>Ожидаем игроков…</li>'}
                </ul>
            </div>
        </div>
        ${isHost ? '<button class="primary-btn" onclick="startGame()">Начать игру</button>' : ''}
    `;
}

function startGame() {
    if (!currentPin) {
        console.warn('Нет текущего PIN для старта игры');
        return;
    }
    socket.emit('start_game', { pin: currentPin });
}

function renderQuestion(data) {
    const box = document.getElementById('game_view');
    if (!box) return;

    box.style.display = 'block';

    const scores = data.scores || { A: 0, B: 0 };

    box.innerHTML = `
        <div class="game-header">
            <div>
                <h2 class="game-theme">${data.theme || 'Игровой раунд'}</h2>
                <p class="turn-indicator">Ход команды ${data.current_team}</p>
                <p class="turn-indicator">Вопрос ${data.question_index + 1} из ${data.total_questions}</p>
            </div>
            <div class="score-board">
                <span class="team-a-score">A: ${scores.A}</span>
                <span class="score-separator">—</span>
                <span class="team-b-score">${scores.B} :B</span>
            </div>
        </div>
        <div class="question-block">
            <h3 class="question-text">${data.text}</h3>
        </div>
        <div class="answers-grid">
            ${data.options.map((opt, idx) => `
                <button class="answer-btn" onclick="sendAnswer(${idx}, '${data.pin}', '${data.current_team}')">
                    ${opt}
                </button>
            `).join('')}
        </div>
    `;
}

function sendAnswer(choice, pin, team) {
    socket.emit('answer', { choice, pin, team });
}

// когда сервер шлёт данные игры
socket.on('game_data', (data) => {
    console.log('Данные игры от сервера:', data);
    currentPin = data.pin || currentPin;
    renderLobbyPreview(data);
});

socket.on('question', (data) => {
    console.log('Вопрос от сервера:', data);
    renderQuestion(data);
});

socket.on('game_finished', (data) => {
    alert(`Игра окончена! Счёт — A: ${data.scores.A}, B: ${data.scores.B}`);
});

socket.on('game_created', (data) => {
    console.log('Игра создана, PIN:', data.pin);
    currentPin = data.pin;
    alert('PIN вашей игры: ' + data.pin);
});

// когда сервер обновляет счёт
socket.on('update_scores', (scores) => {
    console.log('Новый счёт:', scores);
});