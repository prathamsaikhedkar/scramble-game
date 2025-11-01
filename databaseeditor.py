import pandas as pd
import sqlite3 as sql

df = pd.read_csv('4000words.csv', header=None)
df.columns = ['word']


def cond(row):
    return len(row['word'])
    
df['Length'] = df.apply(cond,axis=1)


dfnew = df[df['Length'] >= 3].copy()

dfnew = dfnew[dfnew['Length'] <= 9].copy()

def diff(row):
    if row['Length'] <= 4:
        return 'Easy'
    elif row['Length'] <= 6:
        return 'Medium'
    else:
        return 'Hard'
    
dfnew['Difficulty'] = dfnew.apply(diff, axis=1)

dfnew = dfnew.sort_values(by="Length")


conn = sql.connect("database.db")
cursor = conn.cursor()


cursor.execute('''
               CREATE TABLE IF NOT EXISTS words(
               id INTEGER PRIMARY KEY,
               word text NOT NULL,
               len INTEGER NOT NULL,
               difficulty text NOT NULL
               )
''')



conn.commit()



for index, row in dfnew.iterrows():
    word = row['word'].lower()

    cursor.execute('''
                    INSERT INTO words(word,len,difficulty) VALUES (?,?,?)
                   ''', [word,row['Length'],row['Difficulty']])
    conn.commit()
    


