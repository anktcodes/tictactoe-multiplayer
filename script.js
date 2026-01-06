const API_URL = 'https://YOUR-APP-NAME.onrender.com/api';
let currentUser = null;
let currentGame = null;
let authMode = 'login';
let pollInterval = null;

// Check if user is logged in
function checkAuth() {
    const user = localStorage.getItem('currentUser');
    if (user) {
        currentUser = JSON.parse(user);
        showScreen('menuScreen');
    }
}

function switchAuthTab(mode) {
    authMode = mode;
    const buttons = document.querySelectorAll('.auth-tabs button');
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('authButtonText').textContent = mode === 'login' ? 'Login' : 'Sign Up';
}

async function handleAuth() {
    const email = document.getElementById('authEmail').value.trim();
    const password = document.getElementById('authPassword').value;

    if (!email || !password) {
        showError('authError', 'Email and password required');
        return;
    }

    try {
        const endpoint = authMode === 'login' ? '/login' : '/signup';
        const response = await fetch(API_URL + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            currentUser = { email: data.email };
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            showScreen('menuScreen');
        } else {
            showError('authError', data.error);
        }
    } catch (error) {
        showError('authError', 'Connection error. Make sure the server is running.');
    }
}

function logout() {
    localStorage.removeItem('currentUser');
    currentUser = null;
    showScreen('authScreen');
}

async function createGame() {
    try {
        const response = await fetch(API_URL + '/game/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentUser.email })
        });

        const game = await response.json();

        if (response.ok) {
            currentGame = game;
            document.getElementById('waitingCode').textContent = game.code;
            showScreen('waitingScreen');
            startPolling();
        } else {
            showError('menuError', game.error);
        }
    } catch (error) {
        showError('menuError', 'Connection error');
    }
}

async function joinGame() {
    const code = document.getElementById('joinCode').value.trim().toUpperCase();

    if (!code) {
        showError('menuError', 'Enter a game code');
        return;
    }

    try {
        const response = await fetch(API_URL + '/game/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, email: currentUser.email })
        });

        const game = await response.json();

        if (response.ok) {
            currentGame = game;
            showGameScreen();
            startPolling();
        } else {
            showError('menuError', game.error);
        }
    } catch (error) {
        showError('menuError', 'Connection error');
    }
}

async function makeMove(position) {
    if (!currentGame) return;

    try {
        const response = await fetch(API_URL + '/game/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: currentGame.code,
                email: currentUser.email,
                position
            })
        });

        const game = await response.json();

        if (response.ok) {
            currentGame = game;
            updateGameScreen();
        }
    } catch (error) {
        console.error('Move error:', error);
    }
}

async function pollGame() {
    if (!currentGame) return;

    try {
        const response = await fetch(API_URL + '/game/' + currentGame.code);
        const game = await response.json();

        if (response.ok) {
            currentGame = game;
            
            if (game.status === 'playing' && document.getElementById('waitingScreen').classList.contains('hidden') === false) {
                showGameScreen();
            } else if (game.status === 'playing') {
                updateGameScreen();
            }
        }
    } catch (error) {
        console.error('Poll error:', error);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollGame, 1000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function showGameScreen() {
    showScreen('gameScreen');
    document.getElementById('gameCode').textContent = currentGame.code;
    updateGameScreen();
}

function updateGameScreen() {
    const isPlayer1 = currentUser.email === currentGame.player1_email;
    const mySymbol = isPlayer1 ? 'X' : 'O';
    const isMyTurn = currentGame.current_turn === mySymbol;

    // Update player info
    document.getElementById('player1Info').textContent = 'X: ' + currentGame.player1_email.split('@')[0];
    document.getElementById('player1Info').classList.toggle('active', currentGame.current_turn === 'X');
    
    document.getElementById('player2Info').textContent = 'O: ' + (currentGame.player2_email ? currentGame.player2_email.split('@')[0] : 'Waiting...');
    document.getElementById('player2Info').classList.toggle('active', currentGame.current_turn === 'O');

    // Update turn indicator
    const indicator = document.getElementById('turnIndicator');
    if (currentGame.winner) {
        indicator.className = 'turn-indicator winner';
        indicator.textContent = currentGame.winner === mySymbol ? 'You Won! 🎉' : 'You Lost 😔';
    } else if (isMyTurn) {
        indicator.className = 'turn-indicator your-turn';
        indicator.textContent = 'Your Turn';
    } else {
        indicator.className = 'turn-indicator opponent-turn';
        indicator.textContent = "Opponent's Turn";
    }

    // Update board
    const cells = document.querySelectorAll('.cell');
    const oldestIndex = currentGame.move_history.length === 6 ? currentGame.move_history[0].position : -1;

    cells.forEach((cell, index) => {
        const value = currentGame.board[index];
        cell.textContent = value || '';
        cell.className = 'cell';
        
        if (value === 'X') cell.classList.add('x');
        if (value === 'O') cell.classList.add('o');
        if (index === oldestIndex) cell.classList.add('oldest');
        
        cell.disabled = !!value || !isMyTurn || !!currentGame.winner;
    });

    // Update move counter
    document.getElementById('moveCounter').textContent = `Moves: ${currentGame.move_history.length}/6`;
}

function copyCode() {
    const code = document.getElementById('waitingCode').textContent;
    navigator.clipboard.writeText(code);
    event.target.textContent = 'Copied!';
    setTimeout(() => {
        event.target.textContent = 'Copy Code';
    }, 2000);
}

function backToMenu() {
    stopPolling();
    currentGame = null;
    showScreen('menuScreen');
    document.getElementById('joinCode').value = '';
}

function showScreen(screenId) {
    ['authScreen', 'menuScreen', 'waitingScreen', 'gameScreen'].forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });
    document.getElementById(screenId).classList.remove('hidden');
    hideError('authError');
    hideError('menuError');
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.classList.remove('hidden');
}

function hideError(elementId) {
    document.getElementById(elementId).classList.add('hidden');
}

// Enter key support
document.getElementById('authPassword').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleAuth();
});

document.getElementById('joinCode').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') joinGame();
});

// Initialize
checkAuth();
