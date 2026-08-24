import os
import secrets
import html
import random as rd
import sqlite3 as sql
from datetime import datetime
from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
socketio = SocketIO(app)

room_codes = {}
points = {}
readyplayers = {}
currentword = {}
room_count = 0

def getcode():
    i = rd.randint(1000, 9999)
    while str(i) in room_codes:
        i = rd.randint(1000, 9999)
    return str(i)

def getword():
    i = rd.randint(1, 200)
    if i <= 104:
        i = rd.randint(1, 858)
    elif i <= 154:
        i = rd.randint(859, 1544)
    elif i <= 184:
        i = rd.randint(1545, 2229)
    elif i <= 194:
        i = rd.randint(2230, 2863)
    elif i <= 199:
        i = rd.randint(2864, 3367)
    else:
        i = rd.randint(3368, 3725)
    
    conn = sql.connect("database.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT word, len FROM words WHERE id=?", [i])
        wordlist = cursor.fetchall()
        while not wordlist:
            i = rd.randint(1, 3725)
            cursor.execute("SELECT word, len FROM words WHERE id=?", [i])
            wordlist = cursor.fetchall()
    finally:
        conn.close()

    chosen_word = wordlist[0][0]
    l1 = list(chosen_word)
    wordlen = wordlist[0][1]
    word = chosen_word
    while word == chosen_word:
        rd.shuffle(l1)
        word = "".join(l1)

    if wordlen <= 4:
        difficulty = 'easy'
    elif wordlen <= 6:
        difficulty = 'medium'
    else:
        difficulty = 'hard'

    return (chosen_word, word, wordlen, difficulty)

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        raw_name = request.form.get('entered_name', "")
        raw_rcode = request.form.get('room_code', "")

        name = raw_name.strip()
        rcode = raw_rcode.strip()

        join = request.form.get('join', False)
        create = request.form.get('create', False)
        error = request.form.get('error', False)

        if error is not False:
            return redirect(url_for("home"))

        if not name:
            return render_template('home.html', error='empty name')
        
        if len(name) > 15:
            return render_template('home.html', error='name too long (max 15 characters)')
        
        if join is not False and not rcode:
            return render_template('home.html', error='no room code')

        room = str(rcode)

        if create is not False:
            room = getcode()
            room_codes[room] = {"player_count": 0, "players": {}, 'started': False}
        elif room not in room_codes:
            return render_template('home.html', error='invalid code')
        elif room_codes[room]['started']:
            return render_template('home.html', error='round has already started')
        
        session['name'] = name
        session['room'] = room

        return redirect(url_for("game"))

    return render_template("home.html")

@app.route("/game", methods=["POST", "GET"])
def game():
    room = session.get('room')

    if request.method == "POST":
        error = request.form.get('error', False)
        if error is not False:
            return redirect(url_for("home"))

    if not room or room not in room_codes:
        return render_template("game.html", error="room not found")

    return render_template('game.html')

@app.route("/leaderboard")
def leaderboard():
    conn = sql.connect("database.db")
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, SUM(points) as total_points,
                   (SELECT timestamp FROM scores s2 WHERE s2.name = s1.name ORDER BY points DESC LIMIT 1) as peak_time
            FROM scores s1
            GROUP BY name
            ORDER BY total_points DESC
        ''')
        data = cursor.fetchall()
    finally:
        conn.close()
    
    leaderboard_data = [{'name': row[0], 'total_points': row[1], 'peak_time': row[2]} for row in data]
    return {'leaderboard': leaderboard_data}

@socketio.on('connect')
def connect(auth=None):
    room = session.get('room')
    name = session.get('name')
    if not room or not name:
        return
    if room not in room_codes:
        leave_room(room)
        return 
    
    join_room(room)

    room_codes[room]['player_count'] += 1
    dict1 = {request.sid: name}
    room_codes[room]['players'].update(dict1)

    if room not in points:
        points[room] = {name: 0}
    else:
        points[room].update({name: 0})

    readyplayers[name] = False
    socketio.emit("playeradded", (points[room], room), to=room)

@socketio.on('disconnect')
def disconnect():
    name = session.get('name')
    room = session.get('room')
    sid = request.sid 

    if room in room_codes:
        if sid in room_codes[room]['players']:
            del room_codes[room]['players'][sid]
        
        room_codes[room]['player_count'] -= 1
        
        if room in points and name in points[room]:
            del points[room][name]
        if name in readyplayers:
            del readyplayers[name]
        if room in currentword and name in currentword[room]:
            del currentword[room][name]

        if room_codes[room]['player_count'] <= 0:
            del room_codes[room]
            if room in points:
                del points[room]
            if room in currentword:
                del currentword[room]

@socketio.on("ready")
def ready():
    name = session.get('name')
    room = session.get('room')
    readyplayers[name] = True
    f = 0

    if not room or room not in room_codes:
        return

    for player in room_codes[room]['players'].values():
        if readyplayers.get(player) is False or room_codes[room]['player_count'] <= 1:
            f = 1
            break

    if f == 0:
        currentword[room] = {}
        for player_id in room_codes[room]['players']:
            data = getword()
            currentword[room].update({room_codes[room]['players'][player_id]: data[0]})
            socketio.emit("startgame", data[1:], to=player_id)
        room_codes[room]['started'] = True

@socketio.on("validate")
def validate(guess):
    name = session.get("name")
    room = session.get("room")

    if not room or room not in currentword or not name or name not in currentword[room]:
        return

    if not isinstance(guess, dict):
        return

    guess_value = guess.get('guess', '')
    if not isinstance(guess_value, str):
        return

    if guess_value == currentword[room][name]:
        guess_len = len(guess_value)
        if guess_len < 5:
            i = 10
        elif guess_len < 7:
            i = 30
        else:
            i = 50

        socketio.emit("validatedguess", i, to=request.sid)

        newword = getword()
        currentword[room][name] = newword[0]
        socketio.emit("newword", (newword[1:]), to=request.sid)
        points[room][name] = points[room].get(name, 0) + i
        socketio.emit("ptsupdate", (name, points[room][name]), to=room)
    else:
        socketio.emit("validatedguess", 0, to=request.sid)

@socketio.on("skip")
def skip():
    name = session.get('name')
    room = session.get('room')

    if not room or room not in currentword or not name or name not in currentword[room]:
        return
    
    newword = getword()

    word_len = len(currentword[room][name])
    if word_len < 5:
        i = 10
    elif word_len < 7:
        i = 5
    else:
        i = 2
        
    currentword[room][name] = newword[0]
    socketio.emit("newword", (newword[1:]), to=request.sid)

    points[room][name] = points[room].get(name, 0) - i
    socketio.emit("ptsupdate", (name, points[room][name]), to=room)

@socketio.on("gameover")
def gameover():
    room = session.get("room")
    if not room or room not in points:
        return

    winner = ""
    winnerpts = -1000

    for player, point in points[room].items():
        if winnerpts < point:
            winnerpts = point
            winner = player

    conn = sql.connect("database.db")
    try:
        cursor = conn.cursor()
        for player, point in points[room].items():
            cursor.execute("INSERT INTO scores (name, points) VALUES (?, ?)", (player, point))
        conn.commit()
    finally:
        conn.close()

    if room in points:
        del points[room]

    socketio.emit("gameovertoall", winner, to=room)

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true")
    socketio.run(app, host='127.0.0.1', port=5000, debug=debug_mode)