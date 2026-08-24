# Scramble Battles - Architecture & Technical Design

This document details the system design, communication protocols, state management, database models, and animation architecture of **Scramble Battles**.

---

## 1. System Architecture Overview

Scramble Battles combines a lightweight Flask server with real-time WebSocket channels managed via Flask-SocketIO. Clients interact with the application over two protocols:
1. **HTTP/REST Protocol**: For landing page delivery, session initiation (room creation/joining), and fetching leaderboard statistics.
2. **WebSocket (Socket.IO) Protocol**: For continuous real-time state synchronization, ready checks, guess validation, score updates, and match termination.

```
                    ┌────────────────────────┐
                    │      Web Browser       │
                    │ (HTML5/GSAP/Howler.js) │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
  HTTP Requests                                   Socket.IO Events
  (GET /, POST /,                                 (connect, ready,
   GET /leaderboard)                               validate, skip, gameover)
        │                                               │
        ▼                                               ▼
┌───────────────────────────────────────────────────────────────┐
│                     Flask-SocketIO Engine                     │
│                  [testgame.py / game.py]                     │
├───────────────────────────────────────────────────────────────┤
│ In-Memory Match State:                                        │
│  - room_codes: { <room_id>: { player_count, players, started }│
│  - points: { <room_id>: { <player_name>: <score> } }          │
│  - readyplayers: { <player_name>: <bool> }                    │
│  - currentword: { <room_id>: { <player_name>: <target_word> } │
├───────────────────────────────────────────────────────────────┤
│ Data Layer (SQLite3):                                         │
│  - `words` table: Word dictionary & difficulty levels         │
│  - `scores` table: Final match scores with timestamps         │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Match Lifecycle & State Machine

A match moves through distinct phases from creation to game over:

```mermaid
stateDiagram-v2
    [*] --> Lobby: Player visits "/"
    Lobby --> RoomWaiting: Create Room / Join Room
    RoomWaiting --> RoomReady: Player clicks "I'm Ready"
    RoomReady --> RoundActive: All players ready (player_count >= 2)
    
    state RoundActive {
        [*] --> WordDisplayed: Receive scrambled word
        WordDisplayed --> WordValidating: User finishes typing guess
        WordValidating --> WordCorrect: Guess matches target
        WordValidating --> WordIncorrect: Guess does not match target
        WordCorrect --> WordDisplayed: Award points (+10/+30/+50) & next word
        WordIncorrect --> WordDisplayed: Retry current word
        WordDisplayed --> WordSkipped: User presses Ctrl+S
        WordSkipped --> WordDisplayed: Deduct penalty (-10/-5/-2) & next word
    }
    
    RoundActive --> GameOver: Match timer reaches 0:00
    GameOver --> ScoresPersisted: Server persists scores to database.db
    GameOver --> WinnerAnnounced: gameovertoall event emitted
    WinnerAnnounced --> [*]
```

---

## 3. Real-Time WebSocket Event Sequences

### 3.1 Match Setup & Ready Handshake

```mermaid
sequenceDiagram
    autonumber
    actor Player 1
    actor Player 2
    participant Server as Flask-SocketIO Server
    
    Player 1->>Server: HTTP POST / (Create Room)
    Server-->>Player 1: Set Session (room=5555, name=P1), Redirect /game
    Player 1->>Server: WS Connect (room=5555)
    Server-->>Player 1: WS "playeradded" (points, room=5555)
    
    Player 2->>Server: HTTP POST / (Join Room 5555)
    Server-->>Player 2: Set Session (room=5555, name=P2), Redirect /game
    Player 2->>Server: WS Connect (room=5555)
    Server-->>Player 1: WS "playeradded" (updated points)
    Server-->>Player 2: WS "playeradded" (updated points)
    
    Player 1->>Server: WS "ready"
    Server->>Server: Check if all ready (P2 is false) -> Wait
    
    Player 2->>Server: WS "ready"
    Server->>Server: Check if all ready (P1=true, P2=true, count=2) -> Start Match
    Server->>Server: Fetch words for P1 and P2 from SQLite
    Server-->>Player 1: WS "startgame" (scrambled_word, len, difficulty)
    Server-->>Player 2: WS "startgame" (scrambled_word, len, difficulty)
```

### 3.2 Gameplay Loop: Guessing, Skipping, and Score Sync

```mermaid
sequenceDiagram
    autonumber
    actor Player 1
    actor Player 2
    participant Server as Flask-SocketIO Server
    
    Note over Player 1: Types full word guess
    Player 1->>Server: WS "validate" { guess: "APPLE" }
    alt Guess is Correct
        Server->>Server: Calculate points (+30 for Medium)
        Server-->>Player 1: WS "validatedguess" (30)
        Server->>Server: Generate new word from SQLite
        Server-->>Player 1: WS "newword" (new_scrambled, len, diff)
        Server-->>Player 1: WS "ptsupdate" ("Player1", 30)
        Server-->>Player 2: WS "ptsupdate" ("Player1", 30)
    else Guess is Incorrect
        Server-->>Player 1: WS "validatedguess" (0)
    end
    
    Note over Player 2: Presses Ctrl + S (Skip)
    Player 2->>Server: WS "skip"
    Server->>Server: Calculate penalty (-10 for Easy)
    Server->>Server: Generate new word from SQLite
    Server-->>Player 2: WS "newword" (new_scrambled, len, diff)
    Server-->>Player 1: WS "ptsupdate" ("Player2", -10)
    Server-->>Player 2: WS "ptsupdate" ("Player2", -10)
```

### 3.3 Match Conclusion & Score Persistence

```mermaid
sequenceDiagram
    autonumber
    actor Player 1
    actor Player 2
    participant Server as Flask-SocketIO Server
    participant DB as SQLite database.db
    
    Note over Player 1, Player 2: Round countdown reaches 0
    Player 1->>Server: WS "gameover"
    Server->>Server: Determine highest score player
    Server->>DB: INSERT INTO scores (name, points) VALUES (...)
    DB-->>Server: Commit success
    Server-->>Player 1: WS "gameovertoall" (winner_name)
    Server-->>Player 2: WS "gameovertoall" (winner_name)
```

---

## 4. In-Memory State Model

The server keeps real-time room and player states in memory:

```python
room_codes = {
    "1234": {
        "player_count": 2,
        "players": {
            "<sid_1>": "Alice",
            "<sid_2>": "Bob"
        },
        "started": True
    }
}

points = {
    "1234": {
        "Alice": 80,
        "Bob": 50
    }
}

readyplayers = {
    "Alice": True,
    "Bob": True
}

currentword = {
    "1234": {
        "Alice": "elephant",
        "Bob": "banana"
    }
}
```

---

## 5. Database Schema & Data Pipeline

### 5.1 Tables

#### `words` Table
Stores vocabulary entries extracted and filtered from `4000words.csv`:
```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    word TEXT NOT NULL,
    len INTEGER NOT NULL,
    difficulty TEXT NOT NULL
);
```

#### `scores` Table
Stores historical match scores:
```sql
CREATE TABLE scores (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    points INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Leaderboard Query
The `/leaderboard` endpoint aggregates historical match performance across all games:
```sql
SELECT name, SUM(points) as total_points,
       (SELECT timestamp FROM scores s2 WHERE s2.name = s1.name ORDER BY points DESC LIMIT 1) as peak_time
FROM scores s1
GROUP BY name
ORDER BY total_points DESC;
```

---

## 6. Frontend Animation & Audio Architecture

### 6.1 GSAP MotionPath Border Tracer
The active word input container features an SVG border tracing animation. As the player achieves consecutive correct answers:
- The `streak` counter increases.
- The `streakmul` multiplier scales up.
- The GSAP timeline duration shortens dynamically:
  $$\text{duration} = 4.0 - (\text{streakmul} \times 1.0)$$
- Creating an accelerating tracer effect around the current word.

### 6.2 Anime.js Background Grid
The background renders a dynamic CSS grid of square tiles calculated from `window.innerWidth` and `window.innerHeight`. Anime.js triggers subtle color wave pulses radiating outward from the center grid coordinate on word transitions.

### 6.3 Sound Effects Matrix
Audio cues are preloaded and managed by Howler.js:
- `JeffsJingle.MP3`: Background match soundtrack (loops at 70% volume).
- `ding3.mp3` / `ding5.mp3` / `ding6.mp3`: Randomly sampled success sound effects played on correct answers.
