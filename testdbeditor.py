import sqlite3 as sql


conn = sql.connect("database.db")
cursor = conn.cursor()


# cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[20,"guava",len("guava")])
# conn.commit()
# cursor.execute('''
#                CREATE TABLE IF NOT EXISTS words(
#                id INTEGER PRIMARY KEY,
#                word text NOT NULL,
#                len INTEGER NOT NULL
#                )
# ''')

# conn.commit()


# for i in range(21,25):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"guava",len("guava")])
#     conn.commit()
# for i in range(25,30):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"kiwi",len("kiwi")])
#     conn.commit()
# for i in range(30,35):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"pineapple",len("pineapple")])
#     conn.commit()
# for i in range(35,40):
#     cursor.execute("INSERT INTO words(id,word,len) VALUES (?,?,?)",[i,"watermelon",len("watermelon")])
#     conn.commit()

cursor.execute('''
    SELECT count(*) FROM words;               
''')

print(cursor.fetchall())





conn.close()