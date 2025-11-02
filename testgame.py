from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import sqlite3 as sql
import random as rd
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "idk"
socketio = SocketIO(app)

# conn = sql.connect("data.db")
# cursor = conn.cursor()

# cursor.execute('''
#                CREATE TABLE IF NOT EXISTS words(
#                id INTEGER PRIMARY KEY,
#                word text NOT NULL,
#                len INTEGER NOT NULL
#                )
# ''')

# conn.commit()


# for i in range(1,5):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"pear",len("pear")])
#     conn.commit()
# for i in range(5,10):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"banana",len("banana")])
#     conn.commit()
# for i in range(10,15):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"mango",len("mango")])
#     conn.commit()
# for i in range(15,20):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"strawberry",len("strawberry")])
#     conn.commit()

# conn.close()

room_codes = {}
points = {}
readyplayers = {}
currentword = {}
room_count = 0

def getcode():
    i = rd.randint(1000,9999)
    while i in room_codes:
        i = rd.randint(1000,9999)
    return str(i)
    


def getword():
    i = rd.randint(1,200)
    if i<=104:
        i = rd.randint(1,858)
    elif i<=154:
        i = rd.randint(859,1544)
    elif i<=184:
        i = rd.randint(1545,2229)
    elif i<=194:
        i = rd.randint(2230,2863)
    elif i<=199:
        i = rd.randint(2864,3367)
    else:
        i = rd.randint(3368,3725)
    
    conn = sql.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word,len FROM words WHERE id=?", [i])
    wordlist = cursor.fetchall()
    conn.close()
    chosen_word = wordlist[0][0]
    l1 = list(chosen_word)
    wordlen = wordlist[0][1]
    word=chosen_word
    while word==chosen_word:
        rd.shuffle(l1)
        word = "".join(l1)
    if wordlen<=4:
        difficulty = 'easy'
    elif wordlen<=6:
        difficulty = 'medium'
    else:
        difficulty = 'hard'
    return (chosen_word,word,wordlen,difficulty)


@app.route("/", methods=["POST","GET"])
def home():
    session.clear()
    if request.method=="POST":
        name = request.form.get('entered_name',"")
        rcode = request.form.get('room_code',"")

        join = request.form.get('join', False)
        create = request.form.get('create', False)

        # if name=="":
        #     return render_template('testhome.html',error='empty name')
        
        if join!=False and rcode=="":
            return render_template('testhome.html',error='no room code')

        room = str(rcode)

        if create!=False:
            room = getcode()
            room_codes[room] = {"player_count":0, "players":{}, 'started':False}
        elif room not in room_codes:
            return render_template('testhome.html',error='invalid code')
        elif room_codes[room]['started']:
            return render_template('testhome.html', error='round has already started')
        
        session['name'] = name
        session['room'] = room

        return redirect(url_for("game"))

       
    return render_template("testhome.html")


@app.route("/game")
def game():

    return render_template('testgame.html')

@app.route("/leaderboard")
def leaderboard():
    conn = sql.connect("database.db")
    cursor = conn.cursor()
    # Query: Group by name, sum total points, get time of max single-game score
    cursor.execute('''
        SELECT name, SUM(points) as total_points,
               (SELECT timestamp FROM scores s2 WHERE s2.name = s1.name ORDER BY points DESC LIMIT 1) as peak_time
        FROM scores s1
        GROUP BY name
        ORDER BY total_points DESC
    ''')
    data = cursor.fetchall()
    conn.close()
    
    # Format as JSON list: [{'name': 'Alice', 'total_points': 150, 'peak_time': '2025-10-15 14:30:00'}, ...]
    leaderboard_data = [{'name': row[0], 'total_points': row[1], 'peak_time': row[2]} for row in data]
    return {'leaderboard': leaderboard_data}
    

@socketio.on('connect')
def connect(auth):
    room = session.get('room')
    name = session.get('name')
    if not room or not name:
        return
    if room not in room_codes:
        leave_room(room)
        return
    
    
    join_room(room)

    room_codes[room]['player_count']+=1
    dict1 = {request.sid:name}
    room_codes[room]['players'].update(dict1)
    # print(room_codes)
    print(f"{name} has joined {room}")

    if room not in points:
        points[room] = {name:0}
    else:
        points[room].update({name:0})

    # print(points)

    readyplayers[name] = False
    socketio.emit("playeradded", points[room], to=room)



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

    print(room_codes)
    print(readyplayers)

    for player in room_codes[room]['players'].values():
        if readyplayers[player] == False or room_codes[room]['player_count']<=1:
            f = 1
            break

        
    if f==0:
        currentword[room] = {}
        for id in room_codes[room]['players']:
            data = getword()
            currentword[room].update({room_codes[room]['players'][id]:data[0]})
            socketio.emit("startgame", data[1:], to=id)
        room_codes[room]['started'] = True
        


@socketio.on("validate")
def validate(guess):
    name = session.get("name")
    room = session.get("room")

    if room not in currentword:
        return
    # print(guess)
    # print(currentword[room][name])

    if guess['guess']==currentword[room][name]:

        if len(guess['guess'])<5:
            i = 10
        elif len(guess['guess'])<7:
            i = 30
        else:
            i = 50

        socketio.emit("validatedguess", i , to=request.sid)

        newword = getword()
        print(newword)
        
        
        currentword[room][name] = newword[0]
        socketio.emit("newword", (newword[1:]), to=request.sid)
        points[room][name] = points[room][name] + i
        print(points[room][name])
        socketio.emit("ptsupdate", (name, points[room][name]), to=room)
    else:
        socketio.emit("validatedguess", 0 , to=request.sid)

@socketio.on("skip")
def skip():
    name = session.get('name')
    room = session.get('room')

    if room not in currentword:
        return
    
    newword = getword()
    print(newword)

    if len(currentword[room][name])<5:
        i = 10
    elif len(currentword[room][name])<7:
        i = 5
    else:
        i = 2
        
    currentword[room][name] = newword[0]
    socketio.emit("newword", (newword[1:]), to=request.sid)


    points[room][name] = points[room][name] - i
    print(points[room][name])
    socketio.emit("ptsupdate", (name, points[room][name]), to=room)


@socketio.on("gameover")
def gameover():
    room = session.get("room")

    print("game over")
    winner = ""
    winnerpts = -100

    for player,point in points[room].items():
        if winnerpts < point:
            winnerpts = point
            winner = player

    conn = sql.connect("database.db")
    cursor = conn.cursor()
    for player, point in points[room].items():
        cursor.execute("INSERT INTO scores (name, points) VALUES (?, ?)", (player, point))
    conn.commit()
    conn.close()

    if room in points:
        del points[room]  

    socketio.emit("gameovertoall",winner, to=room)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)