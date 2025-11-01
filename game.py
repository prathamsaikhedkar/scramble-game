from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import sqlite3 as sql
import random as rd


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
    global room_count
    room_count+=1
    return str(room_count)

def getword():
    i = rd.randint(1,200)
    if i<=100:
        i = rd.randint(1,859)
    elif i<=180:
        i = rd.randint(860,2230)
    else:
        i = rd.randint(2231,3726)
    
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

        if name=="":
            return render_template('home.html',error='empty name')
        
        if join!=False and rcode=="":
            return render_template('home.html',error='no room code')

        room = str(rcode)

        if create!=False:
            room = getcode()
            room_codes[room] = {"player_count":0, "players":{}, 'started':False}
        elif room not in room_codes:
            return render_template('home.html',error='invalid code')
        elif room_codes[room]['started']:
            return render_template('home.html', error='round has already started')
        
        session['name'] = name
        session['room'] = room

        return redirect(url_for("game"))

       
    return render_template("home.html")


@app.route("/game")
def game():

    return render_template('game.html')
    

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

    if room in room_codes:
        room_codes[room]['player_count'] -= 1
        if room_codes[room]['player_count']<=0:
            del room_codes[room]

@socketio.on("ready")
def ready():
    name = session.get('name')
    room = session.get('room')
    readyplayers[name] = True
    f = 0

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
            i = 1
        elif len(guess['guess'])<7:
            i = 3
        else:
            i = 5

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
        i = 3
    elif len(currentword[room][name])<7:
        i = 2
    else:
        i = 1
        
    currentword[room][name] = newword[0]
    socketio.emit("newword", (newword[1:]), to=request.sid)


    points[room][name] = points[room][name] - i
    print(points[room][name])
    socketio.emit("ptsupdate", (name, points[room][name]), to=room)


@socketio.on("gameover")
def gameover():
    print("game over")

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)