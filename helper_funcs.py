import sqlite3, time
import random, string, re, requests, json
from coffeehouse.lydia import LydiaAI



def randomString(length):
    return ''.join(random.choice(string.ascii_uppercase) for i in range(length))

def group_data_exists(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT 1 FROM groups WHERE group_id="{group_id}"')
    query = curr.fetchone()
    conn.close()

    if query == None:
        return False
    else:
        return True

def get_cooldown(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE group_id="{group_id}"')
    rows = curr.fetchall()
    conn.close()
    return rows[0][4]

def update_cooldown(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET cooldown = "{int(time.time())}" WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def is_lydia_enabled(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE group_id="{group_id}"')
    rows = curr.fetchall()
    conn.close()
    return rows[0][6]

def ask_lydia(user_id, lydia_query, coffeehouse_api_key):
    lydia = LydiaAI(coffeehouse_api_key)
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM lydia WHERE user_id="{user_id}"')
    rows = curr.fetchall()

    if rows == []:
        session = lydia.create_session()
        curr.execute(f'INSERT INTO lydia VALUES ("{user_id}","{session.id}","{session.expires}")')
        conn.commit()
        conn.close()
        return session.think_thought(lydia_query[1:])
    else:
        if int(time.time()) > int(rows[0][2]):
            curr.execute(f'DELETE FROM lydia WHERE (user_id = "{user_id}")')
            session = lydia.create_session()
            curr.execute(f'INSERT INTO lydia VALUES ("{user_id}","{session.id}","{session.expires}")')
            conn.commit()
            conn.close()
            return session.think_thought(lydia_query[1:])
        else:
            conn.close()
            return lydia.think_thought(rows[0][1], lydia_query[1:])

def get_group_settings(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE group_id="{group_id}"')
    rows = curr.fetchall()
    return rows[0]

    conn.close()

def add_admin(group_id, user_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO groups VALUES ("{group_id}", "{user_id}")')
    conn.commit()
    conn.close()

def remove_admin(group_id, user_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM admins WHERE (group_id = "{group_id}" AND user_id = "{user_id}")')
    conn.commit()
    conn.close()

def is_user_admin(user_id, group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM admins WHERE (user_id="{user_id}" AND group_id = "{group_id}")')
    rows = curr.fetchall()

    conn.close()

    if rows == []:
        return False
    else:
        return True

def get_admins(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM admins WHERE group_id="{group_id}"')
    rows = curr.fetchall()

    admins = []
    for row in rows:
        admins.append(row[1])
    conn.close()
    return admins

def save_welcome(group_id, text):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO welcomes VALUES ("{group_id}", "{text}")')
    conn.commit()
    conn.close()

def get_welcome(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM welcomes WHERE (group_id="{group_id}")')
    rows = curr.fetchall()
    conn.close()

    try:
        return rows[0][1]
    except IndexError:
        return None

def delete_welcome(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM welcomes WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def set_days(group_id, days):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET days = "{days*86400}" WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def reset_group(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM groups WHERE (group_id = "{group_id}")')
    curr.execute(f'DELETE FROM admins WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def toggle_group_lock(group_id, toggle):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET lock = "{toggle}" WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def is_locked(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE (group_id="{group_id}")')
    rows = curr.fetchall()
    conn.close()

    if rows[0][1] == "False":
        return False
    else:
        return True

def toggle_ai(group_id, toggle):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET lydia = "{toggle}" WHERE (group_id = "{group_id}")')
    conn.commit()
    conn.close()

def is_thot(username):

    user = requests.get('http://ws2.kik.com/user/'+username)
    user = json.loads(user.text)

    if re.search('[^a-zA-Z]+', user['firstName']) or re.search('[^a-zA-Z]+', user['lastName']):
        return False

    if str(user['firstName']).lower() in str(username) or str(user['lastName']).lower() in str(username):
        if re.search("(([A-Za-z]+)([0-9]{1,4})([A-Za-z]+))|(([A-Za-z]+)([0-9]{1,4}))|(([0-9]{1,4})([A-Za-z]+))", username):
            return True
        else:
            return False
