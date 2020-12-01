import logging
import sys

from kik_unofficial.datatypes.xmpp.chatting import *
import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse
from typing import Union, List, Tuple

import sys, time, os, re, datetime, requests, json, shutil, base64, binascii, configparser
from bs4 import BeautifulSoup

from helper_funcs import *

config = configparser.ConfigParser()
config.read('config.ini')

username = config['REQUIRED']['username']
password = config['REQUIRED']['password']
device_id = config['REQUIRED']['device_id']
android_id = config['REQUIRED']['android_id']
super = config['REQUIRED']['super']
prefix = config['REQUIRED']['prefix']
lydia_prefix = config['REQUIRED']['lydia_prefix']

coffeehouse_api_key = config['OPTIONAL']['coffeehouse_api_key']
kik_bot_username = config['OPTIONAL']['kik_bot_username']
kik_bot_key = config['OPTIONAL']['kik_bot_key']


def main():
    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # create the bot
    bot = EchoBot()


class EchoBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password, device_id_override = device_id, android_id_override = android_id)
        #GENERIC
        #device id: 62030843678b7376a707ca3d11e87836
        #android id: 849d4ffb0c020de6

    def on_authenticated(self):
        print("Authenticated")

    def on_login_ended(self, response: LoginResponse):
        print("Full name: {} {}".format(response.first_name, response.last_name))


    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        if chat_message.body.lower() == prefix+"pass" and chat_message.from_jid in super:
            with open("passkey.txt","r") as f:
                passkey = f.read()
            self.client.send_chat_message(chat_message.from_jid, prefix+passkey)

        elif chat_message.body.lower() == prefix+"help":
            with open("help.txt","r") as f:
                self.client.send_chat_message(chat_message.from_jid, f.read())

        elif chat_message.body.lower() == prefix+"count":
            self.client.send_chat_message(chat_message.from_jid, "{} groups".format(len(os.listdir("groups/"))))

        else:
            if chat_message.from_jid in super:
                self.client.add_friend(chat_message.from_jid)
            self.client.send_chat_message(chat_message.from_jid, "beep boop")



    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        print("[+] '{}' from group ID {} says: {}".format(chat_message.from_jid, chat_message.group_jid, chat_message.body))

        if not group_data_exists(chat_message.group_jid):
            time.sleep(2)
            if not group_data_exists(chat_message.group_jid):
                self.client.send_chat_message(chat_message.group_jid, f"Please re-add me.\n@{username}\n(Errno. 1001)")
                self.client.leave_group(chat_message.group_jid)

        #LYDIA
        if chat_message.body.startswith(lydia_prefix):

            cooldown = get_cooldown(chat_message.group_jid)
            if (int(time.time()) - cooldown) < 2:
                return
            else:
                update_cooldown(chat_message.group_jid)

            if is_lydia_enabled(chat_message.group_jid) == "False":
                return
            else:
                self.client.send_chat_message(chat_message.group_jid, ask_lydia(chat_message.from_jid, chat_message.body[1:], coffeehouse_api_key))
                return

        #COMMANDS
        elif chat_message.body.startswith(prefix):
            cooldown = int(get_cooldown(chat_message.group_jid))
            if (int(time.time()) - cooldown) < 2:
                return

            update_cooldown(chat_message.group_jid)
            with open("passkey.txt","r") as f:
                passkey = f.read()

            if prefix+passkey[:2] in str(chat_message.body):
                is_admin = True
                is_superadmin = True
                chat_message.body = chat_message.body.replace(passkey, '')
                passkey = randomString(5)
                with open("passkey.txt","w") as f:
                    f.write(passkey)
            elif is_user_admin(chat_message.from_jid, chat_message.group_jid):
                is_admin = True
                is_superadmin = False
            else:
                is_admin = False
                is_superadmin = False


            if chat_message.body.lower() == prefix+"ping":
                self.client.send_chat_message(chat_message.group_jid, "Pong!")
                return

            elif chat_message.body.lower() == prefix+"help":
                with open("help.txt","r") as f:
                    self.client.send_chat_message(chat_message.group_jid, f.read())
                return

            elif chat_message.body.lower() == prefix+"settings":
                settings = get_group_settings(chat_message.group_jid)
                added = datetime.datetime.fromtimestamp(settings[2])
                added = added.strftime('%d-%m-%Y')
                if settings[3] != "False":
                    is_silence = True
                else:
                    is_silence = False
                days = int(int(settings[5])/86400)
                set = ('Group Settings:\n'
                        'Added on: {}\n'
                        'Lock: {}\n'
                        'Silence: {}\n'
                        'Days required: {}\n'
                        'AI: {}'
                        ).format(added, settings[1], is_silence, days, settings[6])
                self.client.send_chat_message(chat_message.group_jid, set)
                return

            elif chat_message.body.lower() == prefix+"admins":
                #this command is slow
                adminslist = get_admins(chat_message.group_jid)
                admins = ""
                for admin in adminslist:
                    if '_a@' in admin:
                        admin = requests.get('https://api.kik.com/v1/user/'+admin.replace('_a@talk.kik.com',''),
                            auth=(kik_bot_username, kik_bot_key)
                            )
                        admin = json.loads(admin.text)
                        admins += admin['firstName']+'\n'
                    else:
                        admins += '@'+admin[:-17]+'\n'
                self.client.send_chat_message(chat_message.group_jid, admins)
                return

            elif chat_message.body.lower() == prefix+"welcome" or chat_message.body.lower() == prefix+"rules":
                welcome = get_welcome(chat_message.group_jid)
                if welcome == None:
                    self.client.send_chat_message(chat_message.group_jid, "No welcome message set.")
                else:
                    self.client.send_chat_message(chat_message.group_jid, welcome)

            elif chat_message.body.lower().startswith(prefix+"welcome "):
                if is_admin:
                        save_welcome(chat_message.group_jid, chat_message.body[9:])
                        self.client.send_chat_message(chat_message.group_jid, "Welcome message set.")
                return

            elif chat_message.body.lower() == prefix+"delete welcome":
                if is_admin:
                    if get_welcome(chat_message.group_jid) != None:
                        delete_welcome(chat_message.group_jid)
                        self.client.send_chat_message(chat_message.group_jid, "Welcome message deleted.")
                    else:
                        self.client.send_chat_message(chat_message.group_jid, "No welcome message set.")
                return

            elif chat_message.body.lower().startswith(prefix+"days "):
                if is_admin:
                    days = int(chat_message.body.split()[1])
                    set_days(chat_message.group_jid, days)
                    self.client.send_chat_message(chat_message.group_jid, "Accounts have to be {} days old to join this group now.".format(days))
                return

            elif chat_message.body.lower() == prefix+"reset":
                if is_admin:
                    reset_group(chat_message.group_jid)
                    self.client.send_chat_message(chat_message.group_jid, "Resetting group..")
                    self.client.leave_group(chat_message.group_jid)
                return

            elif chat_message.body.lower() == prefix+"quit":
                if is_admin:
                    self.client.leave_group(chat_message.group_jid)
                return

            elif chat_message.body.lower() == prefix+"lock":
                if is_admin:
                    toggle_group_lock(chat_message.group_jid, True)
                    self.client.send_chat_message(chat_message.group_jid, "Group locked!")
                return

            elif chat_message.body.lower() == prefix+"unlock":
                if is_admin:
                    toggle_group_lock(chat_message.group_jid, False)
                    self.client.send_chat_message(chat_message.group_jid, "Group unlocked!")
                return

            elif chat_message.body.lower() == prefix+"enable ai":
                if is_admin:
                    toggle_ai(chat_message.group_jid, True)
                    self.client.send_chat_message(chat_message.group_jid, "AI enabled.")
                return

            elif chat_message.body.lower() == prefix+"disable ai":
                if is_admin:
                    toggle_ai(chat_message.group_jid, False)
                    self.client.send_chat_message(chat_message.group_jid, "AI disabled.")
                return

            elif chat_message.body.lower().startswith(prefix+"dgg "):
                query = chat_message.body[5:].replace(" ","+")
                r = requests.get("https://api.duckduckgo.com/?q="+query+"&format=json")
                r = json.loads(r.text)
                if r["AbstractText"] and r["AbstractURL"]:
                    self.client.send_chat_message(chat_message.group_jid, r["AbstractText"]+"\n\nMore:\n"+r["AbstractURL"])
                elif r["AbstractText"]:
                    self.client.send_chat_message(chat_message.group_jid, r["AbstractText"])
                elif r["AbstractURL"]:
                    self.client.send_chat_message(chat_message.group_jid, r["AbstractURL"])
                else:
                    self.client.send_chat_message(chat_message.group_jid, "Sorry, I couldn't find anything ):")
                return


    def on_group_status_received(self, response: IncomingGroupStatus):

        if re.search(" has promoted ", str(response.status)):
            add_admin(response.group_jid, response.status_jid)

        elif re.search(" has removed admin status from ", str(response.status)):
            remove_admin(response.group_jid, response.status_jid)

        elif re.search(" from this group$", str(response.status)) or re.search("^You have removed ", str(response.status)) or re.search(" has banned ", str(response.status)):
            try:
                remove_admin(response.group_jid, response.status_jid)
            except:
                pass

        elif re.search(" has left the chat$", str(response.status)):
            try:
                remove_admin(response.group_jid, response.status_jid)
            except:
                pass

        elif re.search(" has joined the chat$", str(response.status)):
            if is_locked(response.group_jid):
                self.client.remove_peer_from_group(response.group_jid, response.status_jid)
            else:
                welcome = get_welcome(response.group_jid)

                if welcome != None:
                    alias = response.status_jid.replace("_a@talk.kik.com","")
                    user = requests.get('https://api.kik.com/v1/user/'+alias,
                        auth=(kik_bot_username, kik_bot_key)
                        )
                    user = json.loads(user.text)

                    welcome = welcome.replace('{firstname}',user['firstName'])
                    welcome = welcome.replace('{lastname}',user['lastName'])

                    self.client.send_chat_message(response.group_jid, welcome)

            if get_group_settings(response.group_jid)[5] != 0:
                #writing this hurt my soul
                global gjid
                global galias
                global ejid
                global egjid

                gjid = response.group_jid
                galias = response.status_jid
                self.client.xiphias_get_users_by_alias([galias])

            #to check if it's a thot
            ejid = response.status_jid
            egjid = response.group_jid
            self.client.add_friend(response.status_jid)
            return


    def on_peer_info_received(self, response: PeersInfoResponse):
        global ejid
        global egjid

        if is_thot(response.users[0].username):
            self.client.remove_peer_from_group(egjid, ejid)
        return


    def on_xiphias_get_users_response(self, response: Union[UsersResponse, UsersByAliasResponse]):
        global gjid
        global galias

        days = int(get_group_settings(gjid)[5])
        creation = int(time.time()) - response.users[0].creation_date_seconds
        if days > creation:
            self.client.remove_peer_from_group(gjid, galias)


    def on_group_sysmsg_received(self, response: IncomingGroupSysmsg):

        #OPEN DB CONNECTION
        conn = sqlite3.connect('db.sqlite3')
        curr = conn.cursor()
        if re.search(" has added you to the chat$", response.sysmsg):
            #this is needed to find admins
            status = BeautifulSoup(str(response.raw_element), 'html.parser')
            group = status.find('g')

            try:
                if group_data_exists(response.group_jid):
                    #reset admins, they might've changed by the time we joined back
                    curr.execute(f'DELETE FROM admins WHERE (group_id = "{response.group_jid}")')
                    conn.commit()

                    admins = group.find_all('m', a = 1)
                    for admin in admins:
                        curr.execute(f'INSERT INTO admins VALUES ("{response.group_jid}", "{admin.contents[0]}")')
                    conn.commit()

                else:
                    #insert all group data
                    curr.execute(f'INSERT INTO groups VALUES ("{response.group_jid}", "False", "{int(time.time())}", "False", "0", "0","False")')
                    conn.commit()

                    #find admins and insert them too
                    admins = group.find_all('m', a = 1)
                    for admin in admins:
                        curr.execute(f'INSERT INTO admins VALUES ("{response.group_jid}", "{admin.contents[0]}")')
                    conn.commit()
            except Exception as e:
                print(e)
                self.client.send_chat_message(response.group_jid, f"Please re-add me.\n@{username}\n(Errno. 1002)")
                self.client.leave_group(response.group_jid)
            #CLOSE DB CONNECTION
            conn.close()


    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("[-] Connection failed: " + response.message)

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)

    def on_register_error(self, response: SignUpError):
        print("[-] Register error: {}".format(response.message))


if __name__ == '__main__':
    main()
