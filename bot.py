import _thread
import configparser
import datetime
import re
from typing import Union

import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.client import KikClient
from kik_unofficial.datatypes.xmpp.chatting import *
from kik_unofficial.datatypes.xmpp.errors import LoginError
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse
from kik_unofficial.datatypes.xmpp.roster import PeersInfoResponse
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse

from helper_funcs import *

config = configparser.ConfigParser()
config.read('config.ini')

username = config['REQUIRED']['username']
password = config['REQUIRED']['password']
device_id = config['REQUIRED']['device_id']
android_id = config['REQUIRED']['android_id']

super = config['REQUIRED']['super']
owner = config['REQUIRED']['owner']
prefix = config['REQUIRED']['prefix']

kik_bot_username = config['OPTIONAL']['kik_bot_username']
kik_bot_key = config['OPTIONAL']['kik_bot_api_key']


def main():
    bot = IchiBot()


class IchiBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password, device_id_override=device_id, android_id_override=android_id)

    def on_authenticated(self):
        print("Authenticated")
        ensure_bot(username)
        clear_captchas()
        _thread.start_new_thread(check_captchas, (self.client, username,))

    def on_login_ended(self, response: LoginResponse):
        print("Full name: {} {}".format(response.first_name, response.last_name))

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        print("[+] '{}' says: {}".format(chat_message.from_jid, chat_message.body))
        if chat_message.body.lower() == prefix + "pass" and chat_message.from_jid in super:
            with open("passkey.txt", "r") as f:
                passkey = f.read()
            self.client.send_chat_message(chat_message.from_jid, prefix + passkey)
        elif chat_message.body.lower() == prefix + "help":
            with open("help/help.txt", "r") as f:
                self.client.send_chat_message(chat_message.from_jid, f.read())
        elif chat_message.body.lower() == prefix + "help group":
            with open("help/group.txt", "r") as f:
                self.client.send_chat_message(chat_message.from_jid, f.read())
        elif chat_message.body.lower() == prefix + "help federations":
            with open("help/federations.txt", "r") as f:
                self.client.send_chat_message(chat_message.from_jid, f.read())
        elif chat_message.body.lower().startswith(prefix + "createfed "):
            name = chat_message.body.split()[1]
            if len(name) > 50:
                self.client.send_chat_message(chat_message.from_jid, "Federation names can only be 50 characters long.")
                return
            success = create_federation(name, chat_message.from_jid)
            if success:
                self.client.send_chat_message(chat_message.from_jid, f"Federation '{name}' created.")
            elif success == 'alreadyownsfed':
                self.client.send_chat_message(chat_message.from_jid, "You already own a federation!")
            elif success == 'fedexists':
                self.client.send_chat_message(chat_message.from_jid, "A federation with such name already exists!")
        elif chat_message.body.lower().startswith(prefix + "deletefed "):
            name = chat_message.body.split()[1]
            if name == user_owns_federation(chat_message.from_jid):
                delete_federation(chat_message.from_jid, name)
                self.client.send_chat_message(chat_message.from_jid, f"Federation '{name}' deleted.")
            else:
                self.client.send_chat_message(chat_message.from_jid,
                                              "Please make sure you spelled the federation name correctly, "
                                              "it's also case sensitive.")
        elif chat_message.body.lower().startswith(prefix + "fedban "):
            user = chat_message.body.split()[1]
            fed = user_owns_federation(chat_message.from_jid)
            if fed:
                fedban(fed, user)
                self.client.send_chat_message(chat_message.from_jid, f"User '{user}' banned from federation '{fed}'.")
            else:
                self.client.send_chat_message(chat_message.from_jid, f"You don't own a federation.")
        elif chat_message.body.lower().startswith(prefix + "fedunban "):
            user = chat_message.body.split()[1]
            fed = user_owns_federation(chat_message.from_jid)
            if fed:
                fedunban(fed, user)
                self.client.send_chat_message(chat_message.from_jid, f"User '{user}' unbanned from federation '{fed}'.")
            else:
                self.client.send_chat_message(chat_message.from_jid, f"You don't own a federation.")
        elif chat_message.body.lower() == prefix + "fedstats":
            fed = fedstats(chat_message.from_jid)
            if not fed:
                self.client.send_chat_message(chat_message.from_jid, f"You don't own a federation.")
            else:
                msg = (
                    "[Federation Stats]\n"
                    f"Name: {fed[0]}\n"
                    f"Bans: {fed[3]}\n"
                    f"Groups: {fed[4]}\n"
                    f"Key: {fed[2]}\n\n"
                    "Do NOT share your key with anyone!"
                )
                self.client.send_chat_message(chat_message.from_jid, msg)
        elif chat_message.body.lower() == prefix + "fedbans":
            banlist = fedbans(chat_message.from_jid)
            if banlist:
                msg = "[Banned in Federation]\n"
                for ban in banlist:
                    msg += ban + "\n"
                self.client.send_chat_message(chat_message.from_jid, msg[:-1])
            else:
                self.client.send_chat_message(chat_message.from_jid, "You don't own a federation.")
        elif chat_message.body.lower() == prefix + "cred":
            # I can't force you to, but I'd appreciate it if you left this one in. Thank you <3
            self.client.send_chat_message(chat_message.from_jid, "Bot written by Node.\nhttps://github.com/qlg1")
        else:
            self.client.add_friend(chat_message.from_jid)
            self.client.send_chat_message(chat_message.from_jid,
                                          "Hello!\nSend '/help' for help\nYou can now add me to groups.")

    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        if str(chat_message.raw_element).count("</alias-sender>") > 1 and "</alias-sender>" not in str(
                chat_message.body):
            return
        print("[+] '{}' from group ID {} says: {}".format(chat_message.from_jid, chat_message.group_jid,
                                                          chat_message.body))
        if not group_data_exists(chat_message.group_jid):
            time.sleep(2)  # give it some time, this is rarely used but good to have
            if not group_data_exists(chat_message.group_jid):
                self.client.send_chat_message(chat_message.group_jid,
                                              f"Please re-add me.\n@{username}\n(Errno. 1001)\nReport to @{owner} if this keeps happening.")
                self.client.leave_group(chat_message.group_jid)

        # COMMANDS
        elif chat_message.body.startswith(prefix):
            cooldown = int(get_cooldown(chat_message.group_jid))
            if (int(time.time()) - cooldown) < 2:
                return
            update_cooldown(chat_message.group_jid)
            with open("passkey.txt", "r") as f:
                passkey = f.read()
            if prefix + passkey[:2] in str(chat_message.body):
                is_admin = True
                is_superadmin = True
                chat_message.body = chat_message.body.replace(passkey, '')
                passkey = random_string(5)
                with open("passkey.txt", "w") as f:
                    f.write(passkey)
            elif is_user_admin(chat_message.from_jid, chat_message.group_jid):
                is_admin = True
                is_superadmin = False
            else:
                is_admin = False
                is_superadmin = False
            if chat_message.body.lower() == prefix + "ping":
                self.client.send_chat_message(chat_message.group_jid, "Pong!")
            elif chat_message.body.lower() == prefix + "help":
                with open("help/help.txt", "r") as f:
                    self.client.send_chat_message(chat_message.group_jid, f.read())
            elif chat_message.body.lower() == prefix + "help group":
                with open("help/group.txt", "r") as f:
                    self.client.send_chat_message(chat_message.group_jid, f.read())
            elif chat_message.body.lower() == prefix + "help federations":
                with open("help/federations.txt", "r") as f:
                    self.client.send_chat_message(chat_message.group_jid, f.read())
            elif chat_message.body.lower() == prefix + "sudo" and is_superadmin:
                # ONLY for retrieving groups owned by the bot
                self.client.promote_to_admin(chat_message.group_jid, chat_message.from_jid)
            elif chat_message.body.lower() == prefix + "enable captcha":
                if is_admin:
                    enable_captcha(chat_message.group_jid)
                    self.client.send_chat_message(chat_message.group_jid, "Captchas enabled.")
            elif chat_message.body.lower() == prefix + "disable captcha":
                if is_admin:
                    disable_captcha(chat_message.group_jid)
                    self.client.send_chat_message(chat_message.group_jid, "Captchas disabled.")
            elif chat_message.body.lower().startswith(prefix + "joinfed "):
                if is_admin:
                    name = chat_message.body.split()[1]
                    joined = join_federation(chat_message.group_jid, name)
                    if joined:
                        self.client.send_chat_message(chat_message.group_jid, f"Joined federation '{name}'.")
                    else:
                        self.client.send_chat_message(chat_message.group_jid, f"Couldn't join federation '{name}'.")
            elif chat_message.body.lower() == prefix + "leavefed":
                if is_admin:
                    leave_federation(chat_message.group_jid)
                    self.client.send_chat_message(chat_message.group_jid, "Left federation.")
            elif chat_message.body.lower() == prefix + "settings":
                settings = get_group_settings(chat_message.group_jid)
                captcha = False
                if settings[8] == "True":
                    captcha = True
                added = datetime.datetime.fromtimestamp(settings[2])
                added = added.strftime('%d-%m-%Y')
                days = int(int(settings[5]) / 86400)
                if settings[7] == '':
                    fed = 'None'
                else:
                    fed = settings[7]
                settings_text = (
                    '[Group Settings]\n'
                    'Added on: {}\n'
                    'Group ID: {}\n'
                    'Lock: {}\n'
                    'Days required: {}\n'
                    'Captcha: {}\n'
                    'Federation: {}'
                ).format(added, chat_message.group_jid[:-17], settings[1], days, captcha, fed)
                self.client.send_chat_message(chat_message.group_jid, settings_text)
            elif chat_message.body.lower() == prefix + "admins":
                # this command is slow, only exists for debug purposes, and wont work without kik bot API credentials
                adminslist = get_admins(chat_message.group_jid)
                admins = ""
                for admin in adminslist:
                    if '_a@' in admin:
                        admin = requests.get('https://api.kik.com/v1/user/' + admin.replace('_a@talk.kik.com', ''),
                                             auth=(kik_bot_username, kik_bot_key)
                                             )
                        admin = json.loads(admin.text)
                        admins += admin['firstName'] + '\n'
                    else:
                        admins += '@' + admin[:-17] + '\n'
                self.client.send_chat_message(chat_message.group_jid, admins)
            elif chat_message.body.lower() in [prefix + "welcome", prefix + "rules"]:
                welcome = get_welcome(chat_message.group_jid)
                if welcome is None:
                    self.client.send_chat_message(chat_message.group_jid, "No welcome message set.")
                else:
                    self.client.send_chat_message(chat_message.group_jid, welcome)
            elif chat_message.body.lower().startswith(prefix + "rules "):
                if is_admin:
                    if get_welcome(chat_message.group_jid) is not None:
                        delete_welcome(chat_message.group_jid)
                    save_welcome(chat_message.group_jid, chat_message.body[7:])
                    self.client.send_chat_message(chat_message.group_jid, "Rules set.")
            elif chat_message.body.lower() in [prefix + "delete welcome", prefix + "delete rules"]:
                if is_admin:
                    if get_welcome(chat_message.group_jid) is not None:
                        delete_welcome(chat_message.group_jid)
                        self.client.send_chat_message(chat_message.group_jid, "Welcome message deleted.")
                    else:
                        self.client.send_chat_message(chat_message.group_jid, "No welcome message set.")
            elif chat_message.body.lower().startswith(prefix + "days "):
                if is_admin:
                    days = int(chat_message.body.split()[1])
                    set_days(chat_message.group_jid, days)
                    self.client.send_chat_message(chat_message.group_jid,
                                                  "Accounts have to be {} days old to join this group now.".format(
                                                      days))
            elif chat_message.body.lower() == prefix + "reset":
                if is_admin:
                    remove_from_groupcount(username)
                    reset_group(chat_message.group_jid)
                    self.client.send_chat_message(chat_message.group_jid, "Resetting group..")
                    self.client.leave_group(chat_message.group_jid)
            elif chat_message.body.lower() == prefix + "quit":
                if is_admin:
                    remove_from_groupcount(username)
                    self.client.leave_group(chat_message.group_jid)
            elif chat_message.body.lower() == prefix + "lock":
                if is_admin:
                    toggle_group_lock(chat_message.group_jid, "True")
                    self.client.send_chat_message(chat_message.group_jid, "Group locked!")
            elif chat_message.body.lower() == prefix + "unlock":
                if is_admin:
                    toggle_group_lock(chat_message.group_jid, "False")
                    self.client.send_chat_message(chat_message.group_jid, "Group unlocked!")
            elif chat_message.body.lower().startswith(prefix + "censor ") and is_admin:
                censor(chat_message.group_jid, chat_message.body[8:])
                self.client.send_chat_message(chat_message.group_jid, f"Now censoring '{chat_message.body[8:]}'")
            elif chat_message.body.lower().startswith(prefix + "uncensor ") and is_admin:
                uncensor(chat_message.group_jid, chat_message.body[10:])
                self.client.send_chat_message(chat_message.group_jid, f"Uncensored '{chat_message.body[10:]}'")
            elif chat_message.body.lower().startswith(prefix + "delete ") and is_admin:
                remove_trigger(chat_message.group_jid, chat_message.body[8:])
                self.client.send_chat_message(chat_message.group_jid, 'Trigger deleted!')
            elif chat_message.body.lower().startswith(prefix + "triggers"):
                triggers = get_triggers(chat_message.group_jid)
                msg = "[Saved Triggers]\n"
                if triggers:
                    for t in triggers:
                        msg += f"{t}  "
                    msg = msg[:-2][-2048:]  # kik message length limit
                else:
                    msg = "No triggers saved!"
                self.client.send_chat_message(chat_message.group_jid, msg)
            elif chat_message.body.lower().startswith(prefix + "censored"):
                censored = get_censored(chat_message.group_jid)
                msg = "[Censored Words]\n"
                if censored:
                    for c in censored:
                        msg += f"{c}  "
                    msg = msg[:-2][-2048:]  # kik message length limit
                else:
                    msg = "No words censored!"
                self.client.send_chat_message(chat_message.group_jid, msg)
        # OTHER FUNCTIONS
        else:
            if " >> " in chat_message.body and is_user_admin(chat_message.from_jid, chat_message.group_jid):
                tri = str(chat_message.body).split('>>', 1)
                if is_trigger(chat_message.group_jid, tri[0].strip()):
                    remove_trigger(chat_message.group_jid, tri[0].strip())
                add_trigger(chat_message.group_jid, tri[0].strip(), tri[1].strip())
                self.client.send_chat_message(chat_message.group_jid, "Trigger saved!")
            else:
                censored = is_censored(chat_message.group_jid, chat_message.body)
                if censored:
                    self.client.remove_peer_from_group(chat_message.group_jid, chat_message.from_jid)
                    return
                cooldown = int(get_cooldown(chat_message.group_jid))
                if (int(time.time()) - cooldown) >= 2:
                    response = is_trigger(chat_message.group_jid, chat_message.body)
                    if response:
                        update_cooldown(chat_message.group_jid)
                        self.client.send_chat_message(chat_message.group_jid, response)
                    else:
                        success = ping_captcha(chat_message.from_jid, chat_message.body)
                        if success:
                            welcome = get_welcome(chat_message.group_jid)
                            if welcome is None:
                                self.client.send_chat_message(chat_message.group_jid, 'Captcha solved.')
                            else:
                                # will only work if you've set a bot username and API key in config.ini
                                if '{firstname}' in welcome or '{lastname}' in welcome:
                                    if "_a@" in chat_message.from_jid:
                                        alias = chat_message.from_jid[:-15]
                                        user = requests.get(
                                            url='https://api.kik.com/v1/user/' + alias,
                                            auth=(kik_bot_username, kik_bot_key)
                                        )
                                    else:
                                        alias = chat_message.from_jid[:-17]
                                        user = requests.get('http://ws2.kik.com/user/' + alias)
                                    user = json.loads(user.text)
                                    welcome = welcome.replace('{firstname}', str(user['firstName'])[:30])
                                    welcome = welcome.replace('{lastname}', str(user['lastName'])[:30])
                                self.client.send_chat_message(chat_message.group_jid, welcome)

    def on_group_status_received(self, response: IncomingGroupStatus):
        if re.search(" has promoted ", str(response.status)):
            add_admin(response.group_jid, response.status_jid)
        elif re.search(" has removed admin status from ", str(response.status)):
            remove_admin(response.group_jid, response.status_jid)
        elif re.search(" from this group$", str(response.status)) or re.search("^You have removed ",
                                                                               str(response.status)) or re.search(
                " has banned ", str(response.status)):
            try:
                remove_admin(response.group_jid, response.status_jid)
            except:
                pass
        elif re.search(" has left the chat$", str(response.status)):
            try:
                remove_admin(response.group_jid, response.status_jid)
            except:
                pass
        elif re.search(" has joined the chat$", str(response.status)) or re.search(" has joined the chat, invited by ",
                                                                                   str(response.status)):
            settings = get_group_settings(response.group_jid)
            if is_locked(response.group_jid):
                self.client.remove_peer_from_group(response.group_jid, response.status_jid)
            elif settings[8] == "True" and not re.search(" has joined the chat, invited by ", str(response.status)):
                vars = make_captcha(response.status_jid, response.group_jid, username)
                self.client.send_chat_message(response.group_jid,
                                              f"Hi, please solve:\n{vars[0]} + {vars[1]} = ?\nYou have 2 minutes.")
            else:
                welcome = get_welcome(response.group_jid)
                if welcome is not None:
                    if '{firstname}' in welcome or '{lastname}' in welcome:  # will only work if you've set a bot username and API key in config.ini
                        if "_a@" in alias:
                            alias = response.status_jid[:-15]
                            user = requests.get(
                                url='https://api.kik.com/v1/user/' + alias,
                                auth=(kik_bot_username, kik_bot_key)
                            )
                        else:
                            alias = response.status_jid[:-17]
                            user = requests.get('http://ws2.kik.com/user/' + alias)
                        user = json.loads(user.text)
                        welcome = welcome.replace('{firstname}', str(user['firstName'])[:30])
                        welcome = welcome.replace('{lastname}', str(user['lastName'])[:30])
                    self.client.send_chat_message(response.group_jid, welcome)

            if settings[5] != 0:
                # there has to be a better way to go about this, right?
                global gjid, galias
                gjid = response.group_jid
                galias = response.status_jid
                self.client.xiphias_get_users_by_alias([galias])
            # to check if fedbanned
            global ejid, egjid
            ejid = response.status_jid
            egjid = response.group_jid
            self.client.add_friend(response.status_jid)

    def on_peer_info_received(self, response: PeersInfoResponse):
        global ejid, egjid
        if ejid != '':
            settings = get_group_settings(egjid)
            save_user(ejid, response.users[0].jid)
            if is_user_fedbanned(ejid, settings[7]):
                self.client.remove_peer_from_group(egjid, ejid)
            ejid = ''
            egjid = ''

    def on_xiphias_get_users_response(self, response: Union[UsersResponse, UsersByAliasResponse]):
        global gjid, galias
        # checking day count
        days = int(get_group_settings(gjid)[5])
        creation = int(time.time()) - response.users[0].creation_date_seconds
        if days > creation:
            self.client.remove_peer_from_group(gjid, galias)

    def on_group_sysmsg_received(self, response: IncomingGroupSysmsg):
        # OPEN DB CONNECTION
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        if re.search(" has added you to the chat$", response.sysmsg):
            compared = compare_groupcounts(username)
            if compared.lower() != username.lower():

                self.client.send_chat_message(response.group_jid, f"Too many groups!\nPlease add @{compared} instead!")
                self.client.leave_group(response.group_jid)
            else:
                add_to_groupcount(username)
            # to find admins
            status = BeautifulSoup(str(response.raw_element), 'html.parser')
            group = status.find('g')

            try:
                if group_data_exists(response.group_jid):
                    # reset admins, they might've changed by the time we joined back
                    curr.execute(f'DELETE FROM admins WHERE (group_id = "{response.group_jid}")')
                    conn.commit()
                    admins = group.find_all('m', a=1)
                    for admin in admins:
                        curr.execute(f'INSERT INTO admins VALUES ("{response.group_jid}", "{admin.contents[0]}")')
                    conn.commit()

                else:
                    # insert all group data
                    curr.execute(
                        f'INSERT INTO groups VALUES ("{response.group_jid}", "False", "{int(time.time())}", "False", "0", "0","False", "", "")')
                    conn.commit()
                    # find admins and insert them too
                    admins = group.find_all('m', a=1)
                    for admin in admins:
                        curr.execute(f'INSERT INTO admins VALUES ("{response.group_jid}", "{admin.contents[0]}")')
                    conn.commit()
            except Exception as e:
                print(e)
                self.client.send_chat_message(response.group_jid,
                                              f"Please re-add me.\n@{username}\n(Errno. 1002)\nReport to @{owner} if this keeps happening")
                self.client.leave_group(response.group_jid)
            # CLOSE DB CONNECTION
            conn.close()

        elif re.search("You have been removed from the group", response.sysmsg):
            remove_from_groupcount(username)

    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("[-] Connection failed: " + response.message)

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)


if __name__ == '__main__':
    main()
