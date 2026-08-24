# Scramble Battles 🎮🔤

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Flask-SocketIO](https://img.shields.io/badge/Socket.IO-Realtime-red.svg)](https://flask-socketio.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-31%20Passed-brightgreen.svg)]()

**Scramble Battles** is a fast-paced, real-time multiplayer word unscrambling battle game. Players create or join virtual game rooms via 4-digit codes, compete concurrently to solve anagrams across weighted difficulty tiers, maintain answering streaks, and fight for the top position on the global leaderboard.

---

## 🌟 Features

- **Real-Time Multiplayer**: Built on top of WebSockets (Flask-SocketIO) for low-latency synchronization of player scores, match statuses, and round timers.
- **Room-Based Matchmaking**:
  - **Create Room**: Generates an isolated 4-digit match room.
  - **Join Room**: Friends can join an existing room with the room code before the round starts.
- **Dynamic Anagram Generation**:
  - Automatically fetches words from a 4,000-word English vocabulary database.
  - Ensures valid permutations using character shuffling so the scrambled word is never identical to the target.
- **Tiered Difficulty & Adaptive Scoring**:
  - **Easy** ($\le 4$ letters): $+10$ points on correct answer (Skip Penalty: $-10$).
  - **Medium** ($5-6$ letters): $+30$ points on correct answer (Skip Penalty: $-5$).
  - **Hard** ($\ge 7$ letters): $+50$ points on correct answer (Skip Penalty: $-2$).
- **Interactive UI & Visual Effects**:
  - Letter-by-letter auto-advancing inputs with backspace navigation.
  - Animated SVG path border tracer driven by [GSAP MotionPathPlugin](https://greensock.com/motionpath/) that accelerates with answer streaks.
  - Dynamic grid tile background animated with [Anime.js](https://animejs.com/).
  - Word reveal and entrance effects with [GSAP SplitText](https://greensock.com/splittext/).
- **Audio Feedback**: Contextual sound effects using [Howler.js](https://howlerjs.com/) for success chimes (`ding`), background music (`JeffsJingle`), and countdowns.
- **Global Leaderboard**: Historical match score logging with aggregated total points and peak score timestamps.
- **Skip Shortcut**: Fast word skipping via keyboard shortcut (`Ctrl + S` / `Cmd + S`).

---

## 🏗️ Architecture & Tech Stack

```
                        ┌────────────────────────────────────────────────────────┐
                        │                     Browser Client                     │
                        │  - Socket.IO Client v4                                 │
                        │  - GSAP 3.13 (SplitText, MotionPath, ScrambleText)     │
                        │  - Anime.js & Howler.js                                │
                        └──────────────────────────┬─────────────────────────────┘
                                                   │ WebSockets & HTTP
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     Flask Backend                                      │
│  - testgame.py (Active Server) / game.py (Baseline Server)                             │
│  - Routes: GET / POST /, /game, /leaderboard                                           │
│  - Events: connect, disconnect, ready, validate, skip, gameover                        │
│  - In-Memory State: room_codes, points, readyplayers, currentword                      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ SQLite3
                                           ▼
                               ┌───────────────────────┐
                               │      database.db      │
                               │  - `words` table      │
                               │  - `scores` table     │
                               └───────────────────────┘
```

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, Flask, Flask-SocketIO, Eventlet, Gunicorn |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Jinja2 Templates |
| **Animation & FX** | GSAP 3 (SplitText, MotionPath, ScrambleText, EasePack), Anime.js |
| **Audio** | Howler.js |
| **Database** | SQLite3 |
| **Data ETL** | Pandas |
| **Testing** | Python `unittest` |

---

## 📁 Project Structure

```
Scramble Game/
├── 4000words.csv             # Vocabulary word list source
├── checklist.txt             # Development tasks and notes
├── database.db               # SQLite database (words & scores)
├── databaseeditor.py         # Data pipeline script to seed database.db
├── game.py                   # Baseline Flask + Socket.IO server
├── testgame.py               # Active full-featured server (leaderboard, rooms, scoring)
├── testdbeditor.py           # Database management script for scores
├── requirements.txt          # Python dependencies
├── package.json              # NPM dependencies (Anime.js)
├── docs/                     # Detailed architecture and protocol documentation
│   └── ARCHITECTURE.md       # Event sequences, data models, and system design
├── templates/
│   ├── base.html             # Base layout template
│   ├── testbase.html         # Base template with GSAP, Howler, and Font CDNs
│   ├── home.html             # Baseline lobby template
│   ├── testhome.html         # Interactive lobby UI with animated grid and leaderboard modal
│   ├── game.html             # Baseline gameplay template
│   ├── testgame.html         # Active gameplay UI (dynamic inputs, streak tracer, HUD)
│   └── testgame1.html        # Layout prototype template
├── static/
│   ├── fonts/                # Custom TrueType font files
│   ├── js/                   # Local client scripts
│   ├── sounds/               # Sound effect audio files
│   ├── svg/                  # SVG assets & icons
│   ├── style.css             # Baseline stylesheet
│   └── teststyle.css         # Active styles and CSS grid definitions
└── tests/                    # Automated test suite
    ├── __init__.py           # Test package initialization
    ├── test_word_logic.py    # Unit tests for anagram generation and difficulty tiers
    ├── test_database.py      # Unit tests for SQLite schemas and queries
    ├── test_routes.py        # HTTP route tests for Flask endpoints
    ├── test_socketio.py      # Integration tests for testgame.py WebSocket events
    └── test_game_socketio.py # Integration tests for baseline game.py events
```

---

## 🎮 Game Rules & Scoring

### 1. Match Initiation
1. A player creates a room and shares the generated 4-digit code.
2. Opponents join using the room code.
3. Each player clicks **"I'm Ready"**. Once all players are ready, a 3-second visual countdown starts and the match begins.

### 2. Answering & Submitting
- Anagram letters are displayed prominently on the screen.
- Players type letters into individual input cells that auto-advance on keystroke.
- When the last character is entered, the guess is automatically validated.
- Correct guesses award points and increment streak counters. Incorrect guesses prompt an immediate retry without score deduction.

### 3. Word Skipping
- Players can skip a difficult word by pressing **`Ctrl + S`** (or **`Cmd + S`**).
- Skipping deducts points based on the difficulty tier and resets the current streak.

### 4. Scoring Summary Table

| Difficulty | Word Length | Points per Correct Guess | Skip Penalty | Background Theme |
| :--- | :--- | :--- | :--- | :--- |
| **Easy** | $\le 4$ characters | $+10$ pts | $-10$ pts | Light Green |
| **Medium** | $5 - 6$ characters | $+30$ pts | $-5$ pts | Light Yellow |
| **Hard** | $\ge 7$ characters | $+50$ pts | $-2$ pts | Light Coral |

### 5. Game Over & Leaderboard
- When the match timer expires, the server evaluates all scores, announces the winner to all connected room clients, and saves the match records to SQLite.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **pip**

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/prathamsaikhedkar/scramble-game.git
   cd scramble-game
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database (Optional)**:
   The repository already includes a pre-seeded `database.db`. To re-seed the word dictionary from `4000words.csv`:
   ```bash
   python databaseeditor.py
   ```

---

## 🕹️ Running the Application

To start the active, full-featured game server:
```bash
python testgame.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

To run the baseline lightweight server:
```bash
python game.py
```

---

## 🧪 Running the Test Suite

The project includes an automated test suite containing 31 comprehensive unit and integration tests covering routes, WebSocket events, difficulty calculations, anagram generation, and database queries.

Run all tests via Python's standard `unittest` test discovery:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Running Specific Test Modules:
```bash
# Test anagram generation & difficulty categorization
python -m unittest tests.test_word_logic

# Test HTTP routes & session handling
python -m unittest tests.test_routes

# Test database schemas & leaderboard aggregation
python -m unittest tests.test_database

# Test WebSocket event handlers
python -m unittest tests.test_socketio
```

---

## 📡 API & WebSocket Reference

### HTTP Endpoints

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Renders the home lobby page. |
| `POST` | `/` | Handles room creation (`create=true`) or joining (`join=true`). Sets session cookie. |
| `GET` | `/game` | Renders the game arena for the active session room. |
| `GET` | `/leaderboard` | Returns JSON array of top players aggregated by total points. |

### WebSocket Events

| Event Name | Direction | Payload | Description |
| :--- | :--- | :--- | :--- |
| `connect` | Client $\rightarrow$ Server | _None (Reads Session)_ | Joins player into room; initializes score. |
| `playeradded` | Server $\rightarrow$ Client | `(points_dict, room_code)` | Broadcasts updated room player list and room code. |
| `disconnect` | Client $\rightarrow$ Server | _None_ | Leaves room and cleans up state if room is empty. |
| `ready` | Client $\rightarrow$ Server | _None_ | Marks player ready. Starts game when all players ready. |
| `startgame` | Server $\rightarrow$ Client | `(scrambled_word, len, difficulty)` | Dispatched to each player with their unique starting word. |
| `validate` | Client $\rightarrow$ Server | `{"guess": "<word>"}` | Validates user input against active target word. |
| `validatedguess` | Server $\rightarrow$ Client | `points_delta` (e.g. `10`, `0`) | Sends result of guess back to submitting player. |
| `ptsupdate` | Server $\rightarrow$ Client | `(player_name, current_pts)` | Broadcasts updated score to all room members. |
| `newword` | Server $\rightarrow$ Client | `(scrambled_word, len, difficulty)` | Sends next scrambled word to player. |
| `skip` | Client $\rightarrow$ Server | _None_ | Deducts skip penalty, sends new word, and updates room scores. |
| `gameover` | Client $\rightarrow$ Server | _None_ | Triggers winner calculation, database persistence, and end screen. |
| `gameovertoall` | Server $\rightarrow$ Client | `winner_name` | Broadcasts match winner to all room members. |

---

## 📄 License
This project is open source and available under the standard MIT License.
