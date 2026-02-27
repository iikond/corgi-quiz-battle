const socket = io(); // подключаемся к Flask-SocketIO

document.getElementById('enter_game').onclick = join;
document.getElementById('start_game').onclick = create;

function enter_game() {
    join();
}


function join() {
    const name = document.getElementById('player_name').value.trim();
    const pin = document.getElementById('player_pin').value.trim();
    socket.emit('join_game', { name, pin});
}

function create() {
    const theme = document.getElementById('host_theme').value.trim();
    const q_num = document.getElementById('host_num_questions').value.trim();
    console.log('q_num перед отправкой:', q_num);  
    socket.emit('create_game', { theme, q_num });
  }

// когда сервер шлёт данные игры
socket.on('game_data', (data) => {
    console.log('Данные игры от сервера:', data);
    // тут потом покажем экран лобби/игры
});

socket.on('game_created', (data) => {
    console.log('Игра создана, PIN:', data.pin);
    // временно просто alert, потом сделаем красивый экран
    alert('PIN вашей игры: ' + data.pin);
  });

// когда сервер обновляет счёт
socket.on('update_scores', (scores) => {
    console.log('Новый счёт:', scores);
});