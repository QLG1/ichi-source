import sqlite3, time
import random, string, re, requests, json

def randomString(length):
    return ''.join(random.choice(string.ascii_uppercase) for i in range(length))

def check_captchas(client, bot):
    print(f"({bot}) Captcha checks started.")
    while True:
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        curr.execute('SELECT * FROM captchas WHERE (bot=?)', (bot,))
        query = curr.fetchall()

        for captcha in query:
            if (int(time.time()) - int(captcha[3])) > 120:
                curr.execute('DELETE FROM captchas WHERE (jid=?)', (captcha[0],))
                conn.commit()
                client.remove_peer_from_group(captcha[4], captcha[0])

        time.sleep(30)

def clear_captchas():
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute('DELETE FROM captchas')
    conn.commit()
    conn.close()

def ping_captcha(jid, message):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM captchas WHERE (jid=?)', (jid,))
    query = curr.fetchall()

    try:
        if str(query[0][1]) in message and len(message) < 5:
            curr.execute(f'DELETE FROM captchas WHERE (jid=?)', (jid,))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    except IndexError:
        pass


def enable_captcha(group_jid):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET captcha = "True" WHERE (group_id = ?)', (group_jid,))
    conn.commit()
    conn.close()

def disable_captcha(group_jid):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET captcha = "False" WHERE (group_id = ?)', (group_jid,))
    conn.commit()
    conn.close()

def make_captcha(jid, group, bot):
    vars = []
    vars.append(random.randint(0,10))
    vars.append(random.randint(0,10))
    sol = vars[0] + vars[1]
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO captchas VALUES (?,?,?,?,?)', (jid, sol, bot, int(time.time()), group))
    conn.commit()
    conn.close()
    return vars

def fedbans(user):

    fed = user_owns_federation(user)
    if fed != False:
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        curr.execute(f'SELECT * FROM fedbans WHERE (federation=?)', (fed,))
        query = curr.fetchall()

        bans = []
        for result in query:
            bans.append(result[1])
        return bans
    else:
        return False

def fedunban(fedname, user):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM fedbans WHERE (federation = ? AND username = ?)', (fedname, user))
    conn.commit()
    conn.close()

def fedban(fedname, user):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO fedbans VALUES (?,?)', (fedname, user))
    conn.commit()
    conn.close()

def is_user_fedbanned(user, fedname):
    if '_a@' in user:
        user = get_user(user)

    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM fedbans WHERE (LOWER(federation) = LOWER(?)  AND username=? COLLATE NOCASE)', (fedname, user[:-17]))
    query = curr.fetchall()
    conn.close()

    if query == []:
        return False
    else:
        return True

def join_federation(group_jid, name):
    if federation_exists(name):
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        curr.execute(f'UPDATE groups SET federation = ? WHERE (group_id = ?)', (name, group_jid))
        conn.commit()
        conn.close()
        return True
    else:
        return False

def leave_federation(group_jid):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET federation = "" WHERE (group_id = ?)', (group_jid,))
    conn.commit()
    conn.close()

def delete_federation(jid, fedname):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM federations WHERE (owner = ?)', (jid,))
    curr.execute(f'DELETE FROM fedbans WHERE (federation = ?)', (fedname,))
    curr.execute(f'UPDATE groups SET federation = "" WHERE (federation = ?)', (fedname,))
    conn.commit()
    conn.close()

def fedstats(owner):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM federations WHERE owner=?', (owner,))
    query1 = curr.fetchall()

    if query1 == []:
        conn.close()
        return False
    else:
        curr.execute(f'SELECT * FROM groups WHERE federation=? COLLATE NOCASE', (query1[0][0],))
        query2 = curr.fetchall()
        conn.close()
        bans = fedbans(owner)
        if query2 == []:
            gcount = 0
        else:
            gcount = len(query2)
        tuple = (len(bans), gcount)
        query1[0] += tuple
        return query1[0]

def user_owns_federation(user):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM federations WHERE owner=?', (user,))
    query = curr.fetchall()
    conn.close()

    if query == []:
        return False
    else:
        return query[0][0]

def federation_exists(name):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM federations WHERE name=? COLLATE NOCASE', (name,))
    query = curr.fetchall()
    conn.close()

    if query == []:
        return False
    else:
        return True

def key_exists(key):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM federations WHERE key=?', (key,))
    query = curr.fetchall()
    conn.close()

    if query == []:
        return False
    else:
        return True

def create_key():
    key = randomString(12)
    while key_exists(key):
        key = randomString(12)
    return key

def create_federation(name, owner):
    if user_owns_federation(owner) == False:
        if federation_exists(name) == False:
            conn = sqlite3.connect('db.sqlite3')
            curr = conn.cursor()
            curr.execute(f'INSERT INTO federations VALUES (?,?,?)', (name, owner, create_key()))
            conn.commit()
            conn.close()
            return True
        else:
            return 'fedexists'
    else:
        return 'alreadyownsfed'

def save_user(alias, jid):
    if get_user(alias) == False:
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        curr.execute(f'INSERT INTO namebase VALUES (?,?)', (alias, jid))
        conn.commit()
        conn.close()

def get_user(alias):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM namebase WHERE (alias=?)', (alias,))
    query = curr.fetchall()
    conn.close()

    if query != []:
        return query[0][1]
    else:
        return False

def get_triggers(group_jid):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM triggers WHERE (group_jid = ?)', (group_jid,))
    query = curr.fetchall()
    conn.close()

    triggers = []
    for q in query:
        triggers.append(q[1])
    return triggers

def get_censored(group_jid):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM censored WHERE (group_jid = ?)', (group_jid,))
    query = curr.fetchall()
    conn.close()

    censored = []
    for q in query:
        censored.append(q[1])
    return censored

def censor(group_jid, word):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO censored VALUES (?,?)', (group_jid, word.lower()))
    conn.commit()
    conn.close()

def uncensor(group_jid, word):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM censored WHERE (group_jid = ? AND word = ?)', (group_jid, word.lower()))
    conn.commit()
    conn.close()

def is_censored(group_jid, message):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM censored WHERE (group_jid = ?)', (group_jid,))
    query = curr.fetchall()
    conn.close()

    for q in query:
        if q[1] in message.lower():
            return True
    return False

def add_trigger(group_jid, trigger, response):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    trigger = trigger.replace('"',"\DQUOTE")
    response = response.replace('"',"\DQUOTE")
    curr.execute(f'INSERT INTO triggers VALUES (?,?,?)', (group_jid, trigger.lower(), response))
    conn.commit()
    conn.close()

def remove_trigger(group_jid, trigger):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    trigger = trigger.replace('"',"\DQUOTE")
    curr.execute(f'DELETE FROM triggers WHERE (group_jid = ? AND trigger = ?)', (group_jid, trigger.lower()))
    conn.commit()
    conn.close()

def is_trigger(group_jid, message):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    message = message.replace('"',"\DQUOTE")
    curr.execute(f'SELECT * FROM triggers WHERE (trigger=? AND group_jid=?)', (message.lower(), group_jid))
    query = curr.fetchall()
    conn.close()

    if query != []:
        return query[0][2].replace('\DQUOTE','"')
    else:
        return False

def ensure_bot(username):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()

    curr.execute(f'SELECT 1 FROM groupcounts WHERE username=?', (username,))
    query = curr.fetchone()

    if query == None:
        curr.execute('INSERT INTO groupcounts VALUES (?, 0)', (username,))
        conn.commit()
    conn.close()
    return

def get_bot_groupcount(username):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groupcounts where username=?', (username,))
    query = curr.fetchall()
    conn.close()

    return query[0][1]

def compare_groupcounts(username):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groupcounts')
    bots = curr.fetchall()
    conn.close()

    smallest_bot = username
    smallest_count = get_bot_groupcount(username)
    for bot in bots:
        if bot[1]+10 < smallest_count:
            smallest_bot = bot[0]
    return smallest_bot

def add_to_groupcount(username):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groupcounts where username=?', (username,))
    bot = curr.fetchall()

    count = bot[0][1]
    curr.execute(f'UPDATE groupcounts SET count = ? WHERE (username = ?)', (int(count)+1, username))
    conn.commit()
    conn.close()

def remove_from_groupcount(username):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groupcounts where username=?', (username,))
    bot = curr.fetchall()

    count = bot[0][1]
    curr.execute(f'UPDATE groupcounts SET count = ? WHERE (username = ?)', (int(count)-1, username))
    conn.commit()
    conn.close()

def group_data_exists(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT 1 FROM groups WHERE group_id=?', (group_id,))
    query = curr.fetchone()
    conn.close()

    if query == None:
        return False
    else:
        return True

def get_cooldown(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE group_id=?', (group_id,))
    rows = curr.fetchall()
    conn.close()
    return rows[0][4]

def update_cooldown(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET cooldown = ? WHERE (group_id = ?)', (int(time.time()), group_id))
    conn.commit()
    conn.close()

def get_group_settings(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE group_id=?', (group_id,))
    rows = curr.fetchall()
    conn.close()
    return rows[0]

def add_admin(group_id, user_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'INSERT INTO admins VALUES (?, ?)', (group_id, user_id))
    conn.commit()
    conn.close()

def remove_admin(group_id, user_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM admins WHERE (group_id = ? AND user_id = ?)', (group_id, user_id))
    conn.commit()
    conn.close()

def is_user_admin(user_id, group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM admins WHERE (user_id=? AND group_id = ?)', (user_id, group_id))
    rows = curr.fetchall()

    conn.close()

    if rows == []:
        return False
    else:
        return True

def get_admins(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM admins WHERE group_id=?', (group_jid,))
    rows = curr.fetchall()

    admins = []
    for row in rows:
        admins.append(row[1])
    conn.close()
    return admins

def save_welcome(group_id, text):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    text = text.replace('"',"\DQUOTE")
    curr.execute(f'INSERT INTO welcomes VALUES (?, ?)', (group_id, text))
    conn.commit()
    conn.close()

def get_welcome(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM welcomes WHERE (group_id=?)', (group_id,))
    rows = curr.fetchall()
    conn.close()

    try:
        return rows[0][1].replace('\DQUOTE','"')
    except IndexError:
        return None

def delete_welcome(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM welcomes WHERE (group_id = ?)', (group_id,))
    conn.commit()
    conn.close()

def set_days(group_id, days):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET days = ? WHERE (group_id = ?)', (days*86400, group_id))
    conn.commit()
    conn.close()

def reset_group(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'DELETE FROM groups WHERE (group_id = ?)', (group_id,))
    curr.execute(f'DELETE FROM admins WHERE (group_id = ?)', (group_id,))
    curr.execute(f'DELETE FROM triggers WHERE (group_jid = ?)', (group_id,))
    curr.execute(f'DELETE FROM censored WHERE (group_jid = ?)', (group_id,))
    conn.commit()
    conn.close()

def toggle_group_lock(group_id, toggle):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'UPDATE groups SET lock = ? WHERE (group_id = ?)', (toggle, group_id))
    conn.commit()
    conn.close()

def is_locked(group_id):
    conn = sqlite3.connect('db.sqlite3')
    curr = conn.cursor()
    curr.execute(f'SELECT * FROM groups WHERE (group_id=?)', (group_id,))
    rows = curr.fetchall()
    conn.close()

    if rows[0][1] == "False":
        return False
    else:
        return True
