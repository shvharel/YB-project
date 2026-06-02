import base64
import socket
import threading
import sqlite3
from tcp_by_size import send_with_size, recv_by_size
import secrets, hashlib
from TCP_AES import recv_with_AES, send_with_AES
import os
import datetime, time
import queue
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

PEPPER = 'HelloPepperebhsdj'
IV = 'hefuhrgjhsdfirps'
mailboxes = {}
mailboxes_lock = threading.Lock()
whos_in_call = {}
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp_sock.bind(('0.0.0.0', 5001))
udp_addr_map = {}
udp_keys = {}
mailboxes_udp = {}
udp_addr_map_reverse = {}



def hashing_for_sign_up(data):
    global PEPPER
    salt = os.urandom(16)
    salted_pass = data.encode() + salt + PEPPER.encode()
    sha = hashlib.sha256()
    sha.update(salted_pass)
    return sha.hexdigest(), salt

def generate_hash(password,salt):
    global PEPPER
    salted_pass = password.encode() + salt + PEPPER.encode()
    sha = hashlib.sha256()
    sha.update(salted_pass)
    return sha.hexdigest()

def generate_large_prime():
    p_hex = """
        FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
        29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
        EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
        E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
        EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE65381
        FFFFFFFF FFFFFFFF
    """.replace('\n', '').replace(' ', '')
    return int(p_hex, 16)

def diffie_hellman(s:socket.socket):
    p = generate_large_prime()
    g = 5
    send_with_size(s,f'DIFHEL|{str(p)}|{str(g)}')
    a = secrets.randbelow(p-2)+1
    A = pow(g,a,p)
    send_with_size(s,f'DIFHEL|{str(A)}')
    data = recv_by_size(s).decode('utf-8')
    splited_data = data.split('|')
    B = int(splited_data[1])
    key = pow(B, a, p)
    shared_secret_bytes = key.to_bytes((key.bit_length() + 7) // 8, 'big')
    return hashlib.sha256(shared_secret_bytes).digest()

def background_cleanup():
    global db
    while True:
        time.sleep(3600)
        print("[Cleanup] Starting hourly cleanup...")
        db.clean_dead_users()

class DataBase:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.lock = threading.Lock()


    def setup_db(self):
        with self.lock:
            self.open_db()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserName TEXT UNIQUE,
                HashPass TEXT,
                Salt BLOB,
                ProfilePicturePath TEXT,
                FinishedReg INTEGER,
                LastConnected DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Hobbies (
                HobbyID INTEGER PRIMARY KEY AUTOINCREMENT,
                HobbyName TEXT UNIQUE
                )""")

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS UserHobbies (
                UserID INTEGER,
                HobbyID INTEGER,
                PRIMARY KEY (UserID, HobbyID),
                FOREIGN KEY (UserID) REFERENCES Users(UserID),
                FOREIGN KEY (HobbyID) REFERENCES Hobbies(HobbyID)
                )""")

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Invites (
                InviteId INTEGER PRIMARY KEY AUTOINCREMENT,
                Sender TEXT,
                Recipient TEXT,
                A TEXT
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Chats (
                ChatId INTEGER PRIMARY KEY AUTOINCREMENT,
                FirstUser TEXT,
                SecondUser TEXT
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS PreKeys (
                UserNameOfSender TEXT PRIMARY KEY,
                UserNameOfRecipient Text,
                PublicKey TEXT
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Messages (
                MessageID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserNameOfSender TEXT,
                UserNameOfRecipient Text,
                Content TEXT,
                Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.fill_interests_once()
            self.close_db()

    def open_db(self):
        self.conn = sqlite3.connect('Users.db', check_same_thread=False, timeout=10)
        self.cursor = self.conn.cursor()

    def fill_interests_once(self):
        hobbies = ["Gaming", "Hiking", "Sports", "Drawing", "Photography", "Cooking", "Writing", "Music", "Reading", "Movies", "Coding", "Traveling", "Gardening", "Board Games", "Shopping", "Crafting", "Diving", "Robotics", "Cars", "Fishing"]

        for hobby in hobbies:
            self.cursor.execute("INSERT OR IGNORE INTO Hobbies (HobbyName) VALUES (?)", (hobby,))
        self.commit()

    def enter_user_hobbies(self, user_id, hobbies):
        self.open_db()
        try:
            for hobby in hobbies:
                self.cursor.execute("SELECT HobbyId FROM Hobbies WHERE HobbyName = ?", (hobby,))
                res = self.cursor.fetchone()
                print(res)
                if res:
                    self.cursor.execute("INSERT OR IGNORE INTO UserHobbies (UserID, HobbyID) VALUES (?, ?)", (user_id, res[0]))
            self.commit()
        finally:
            self.close_db()

    def close_db(self):
        self.conn.close()

    def commit(self):
        self.conn.commit()

    def get_users(self):
        with self.lock:
            self.open_db()
            sql = "SELECT * FROM Users"
            try:
                res = self.cursor.execute(sql)
                self.commit()
            except sqlite3.IntegrityError as e:
                print("Integrity error:", e)  # e.g. duplicate primary key, NOT NULL violation
            except sqlite3.OperationalError as e:
                print("SQL error:", e)  # e.g. bad SQL statement
            except Exception as e:
                print("Other error:", e)
            else:
                return res.fetchall()
            finally:
                self.close_db()


    def for_login(self, username, password):
        with self.lock:
            self.open_db()
            try:
                sql = "SELECT Salt FROM Users WHERE UserName = ?"
                self.cursor.execute(sql, (username,))
                result = self.cursor.fetchone()
                if result is None:
                    return "BAD", None
                salt = result[0]
                hashed = generate_hash(password, salt)
                sql = "SELECT FinishedReg, LastConnected FROM Users WHERE UserName = ? AND HashPass = ?"
                self.cursor.execute(sql, (username, hashed))
                result = self.cursor.fetchone()
                if result is None:
                    return "BAD", None
                print(result[0])
                if result[0] < 3:
                    time_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    time_diff = time_now - (datetime.datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S'))
                    if time_diff.total_seconds() > 1800:
                        sql = "DELETE FROM Users WHERE UserName = ? AND HashPass = ?"
                        self.cursor.execute(sql, (username, hashed))
                        self.commit()
                        return "BAD", None
                    else:
                        sql = "SELECT UserID FROM Users WHERE UserName = ? AND HashPass = ?"
                        self.cursor.execute(sql, (username, hashed))
                        result_id = self.cursor.fetchone()
                        print(result_id)
                        result = [result[0], result_id[0]]
                        return "SEMI", result
                else:
                    sql = "SELECT UserID, UserName, HashPass FROM Users WHERE UserName = ? AND HashPass = ?"
                    self.cursor.execute(sql, (username, hashed))
                    result = self.cursor.fetchone()
                    return "GOOD", result
            except Exception as e:
                print(e)
            finally:
                self.close_db()

    def check_if_available(self, username, password, salt):
        with self.lock:
            self.open_db()
            try:
                sql = "SELECT UserID, FinishedReg, LastConnected FROM Users WHERE UserName = ?"
                self.cursor.execute(sql, (username,))
                data = self.cursor.fetchone()
                self.close_db()
                if data is None:
                    return self.insert_new_user_no_lock(username, password, salt)
                time_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                time_diff = time_now - (datetime.datetime.strptime(data[2], '%Y-%m-%d %H:%M:%S'))
                if data[1] < 3 and time_diff.total_seconds() > 1800:
                    if data[1] == 2:
                        self.open_db()
                        sql = "DELETE FROM UserHobbies WHERE UserID = ?"
                        self.cursor.execute(sql, (data[0],))
                        sql = "DELETE FROM Users WHERE UserName = ?"
                        self.cursor.execute(sql, (username,))
                        self.commit()
                        self.close_db()
                    else:
                        self.open_db()
                        sql = "DELETE FROM Users WHERE UserName = ?"
                        self.cursor.execute(sql, (username,))
                        self.commit()
                        self.close_db()
                    return self.insert_new_user_no_lock(username, password, salt)
                else:
                    return "BAD"
            except Exception as e:
                print(e)
                return "BAD"


    def check_if_passed(self, userID):
        self.open_db()
        try:
            sql = "SELECT FinishedReg, LastConnected FROM Users WHERE UserID = ?"
            self.cursor.execute(sql, (userID,))
            data = self.cursor.fetchone()
            time_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            time_diff = time_now - (datetime.datetime.strptime(data[1], '%Y-%m-%d %H:%M:%S'))
            if data is None:
                return False
            elif data[0] < 3 and time_diff.total_seconds() > 1800:
                if data[0] == 2:
                    sql = "DELETE FROM UserHobbies WHERE UserID = ?"
                    self.cursor.execute(sql, (userID,))
                    sql = "DELETE FROM Users WHERE UserID = ?"
                    self.cursor.execute(sql, (userID,))
                    self.commit()
                else:
                    sql = "DELETE FROM Users WHERE UserID = ?"
                    self.cursor.execute(sql, (userID,))
                    self.commit()
                return False
            else:
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            self.close_db()


    def update_reg(self, user_id, step):
        self.open_db()
        sql = "UPDATE Users SET FinishedReg = ? WHERE UserID = ?"
        try:
            self.cursor.execute(sql, (step, user_id))
            self.commit()
        except Exception as e:
            print(e)
        finally:
            self.close_db()

    def check_if_hobbies(self, user_id, hobbies):
        with self.lock:
            result = self.check_if_passed(user_id)
            if result:
                self.enter_user_hobbies(user_id, hobbies)
                self.update_reg(user_id, 2)
                return True
            else:
                return False

    def check_if_pfp(self, user_id, name):
        with self.lock:
            result = self.check_if_passed(user_id)
            if result:
                sql = "UPDATE Users SET FinishedReg = ?, ProfilePicturePath = ? WHERE UserID = ?"
                try:
                    self.open_db()
                    self.cursor.execute(sql, (3, name, user_id))
                    self.commit()
                    self.close_db()
                except Exception as e:
                    print(e)
                else:
                    return True
            else:
                return False


    def insert_new_user_no_lock(self, username, hashpass, salt):
        self.open_db()
        sql = "INSERT INTO Users (UserName, HashPass, Salt, ProfilePicturePath, FinishedReg)"
        sql += " VALUES(?, ?, ?, 'defaultpfp.png', 1)"
        try:
            self.cursor.execute(sql, (username, hashpass, salt))
            self.commit()
            return "GOOD", self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print("Integrity error:", e)
            return "BAD", None
        except sqlite3.OperationalError as e:
            print("SQL error:", e)  # e.g. bad SQL statement
            return "ERROR", None
        except Exception as e:
            print("Other error:", e)
            return "ERROR", None
        finally:
            self.close_db()


    def insert_new_user(self, username, hashpass, salt):
        with self.lock:
            self.open_db()
            sql = "INSERT INTO Users (UserName, HashPass, Salt, ProfilePicturePath, FinishedReg)"
            sql += " VALUES(?, ?, ?, 'defaultpfp.png', 1)"
            try:
                self.cursor.execute(sql, (username, hashpass, salt))
                self.commit()
                return "GOOD", self.cursor.lastrowid
            except sqlite3.IntegrityError as e:
                print("Integrity error:", e)
                return "BAD", None
            except sqlite3.OperationalError as e:
                print("SQL error:", e)  # e.g. bad SQL statement
                return "ERROR", None
            except Exception as e:
                print("Other error:", e)
                return "ERROR", None
            finally:
                self.close_db()

    def get_invites_offline(self, username_of_recipient):
        self.open_db()
        try:
            sql = "SELECT Sender, A FROM Invites WHERE Recipient = ?"
            self.cursor.execute(sql, (username_of_recipient,))
            return self.cursor.fetchall()
        except Exception as e:
            print(e)
            return []
        finally:
            self.close_db()

    def add_invite(self, username_of_sender, username_of_recipient, A):
        with self.lock:
            self.open_db()
            try:
                sql = "INSERT INTO Invites (Sender, Recipient, A) VALUES (?, ?, ?)"
                self.cursor.execute(sql, (username_of_sender, username_of_recipient, A))
                self.commit()
                return
            except sqlite3.IntegrityError as e:
                print("Integrity error:", e)
                return
            except sqlite3.OperationalError as e:
                print("SQL error:", e)  # e.g. bad SQL statement
                return
            except Exception as e:
                print("Other error:", e)
                return
            finally:
                self.close_db()

    def get_chats(self, username):
        self.open_db()
        try:
            sql = sql = """SELECT CASE WHEN FirstUser = ? THEN SecondUser ELSE FirstUser END FROM Chats WHERE FirstUser = ? OR SecondUser = ?"""
            self.cursor.execute(sql, (username, username, username))
            return self.cursor.fetchall()
        except Exception as e:
            print(e)
            return []
        finally:
            self.close_db()

    def add_chat(self, username_of_first, username_of_second):
        with self.lock:
            self.open_db()
            try:
                sql = "INSERT INTO Chats (FirstUser, SecondUser) VALUES (?, ?)"
                self.cursor.execute(sql, (username_of_first, username_of_second))
                self.commit()
                return
            except sqlite3.IntegrityError as e:
                print("Integrity error:", e)
                return
            except sqlite3.OperationalError as e:
                print("SQL error:", e)  # e.g. bad SQL statement
                return
            except Exception as e:
                print("Other error:", e)
                return
            finally:
                self.close_db()

    def clear_offline_invites(self, username):
        with self.lock:
            self.open_db()
            try:
                self.cursor.execute("DELETE FROM Invites WHERE Recipient = ?", (username,))
                self.commit()
            except Exception as e:
                print(e)
            finally:
                self.close_db()


    def get_pfp_name_by_username(self, username):
        self.open_db()
        try:
            sql = "SELECT ProfilePicturePath FROM Users WHERE UserName = ?"
            self.cursor.execute(sql, (username,))
            return self.cursor.fetchall()
        except Exception as e:
            print(e)
            return []
        finally:
            self.close_db()


    def insert_new_key(self, username, recipient, public):
        with self.lock:
            self.open_db()
            try:
                sql = "INSERT INTO PreKeys (UserNameOfSender, UserNameOfRecipient, PublicKey) VALUES (?, ?, ?)"
                self.cursor.execute(sql, (username, recipient, public))
                self.commit()
                return
            except sqlite3.IntegrityError as e:
                print("Integrity error:", e)
                return
            except sqlite3.OperationalError as e:
                print("SQL error:", e)  # e.g. bad SQL statement
                return
            except Exception as e:
                print("Other error:", e)
                return
            finally:
                self.close_db()

    def get_keys(self, username):
        self.open_db()
        try:
            sql = "SELECT PublicKey, UserNameOfSender FROM PreKeys WHERE UserNameOfRecipient = ?"
            self.cursor.execute(sql, (username,))
            return self.cursor.fetchall()
        except Exception as e:
            print(e)
            return []
        finally:
            self.close_db()

    def delete_keys(self, username):
        with self.lock:
            self.open_db()
            try:
                self.cursor.execute("DELETE FROM PreKeys WHERE UserNameOfRecipient = ?", (username,))
                self.commit()
            except Exception as e:
                print(e)
            finally:
                self.close_db()

    def insert_new_message(self, sender, recipient, content):
        with self.lock:
            self.open_db()
            try:
                sql = "INSERT INTO Messages (UserNameOfSender, UserNameOfRecipient, Content) VALUES (?, ?, ?)"
                self.cursor.execute(sql, (sender, recipient, content))
                self.commit()
                self.cursor.execute("SELECT Timestamp FROM Messages WHERE MessageID = ?", (self.cursor.lastrowid,))
                return self.cursor.fetchone()[0]
            except Exception as e:
                print(e)
                return None
            finally:
                self.close_db()

    def get_messages_between(self, user1, user2):
        self.open_db()
        try:
            sql = """
                SELECT UserNameOfSender, Content, Timestamp FROM Messages
                WHERE (UserNameOfSender = ? AND UserNameOfRecipient = ?)
                OR (UserNameOfSender = ? AND UserNameOfRecipient = ?)
                ORDER BY Timestamp ASC
            """
            self.cursor.execute(sql, (user1, user2, user2, user1))
            return self.cursor.fetchall()
        except Exception as e:
            print(e)
            return []
        finally:
            self.close_db()

    def get_users_by_shared_hobbies(self, user_id, limit=20, offset=0):
        with self.lock:
            self.open_db()
            try:
                sql = """
                    SELECT u.UserID, u.UserName, u.ProfilePicturePath, 
                           COUNT(*) AS shared_count,
                           GROUP_CONCAT(h.HobbyName, ',') AS shared_hobbies
                    FROM Users u
                    JOIN UserHobbies uh ON u.UserID = uh.UserID
                    JOIN Hobbies h ON uh.HobbyID = h.HobbyID
                    WHERE uh.HobbyID IN (
                        SELECT HobbyID FROM UserHobbies WHERE UserID = ?
                    )
                    AND u.UserID != ?
                    AND u.FinishedReg = 3
                    AND u.UserName NOT IN (
                        SELECT CASE WHEN FirstUser = (SELECT UserName FROM Users WHERE UserID = ?)
                                    THEN SecondUser ELSE FirstUser END
                        FROM Chats
                        WHERE FirstUser = (SELECT UserName FROM Users WHERE UserID = ?)
                        OR SecondUser = (SELECT UserName FROM Users WHERE UserID = ?)
                    )
                    AND u.UserName NOT IN (
                        SELECT Recipient FROM Invites WHERE Sender = (SELECT UserName FROM Users WHERE UserID = ?)
                    )
                    AND u.UserName NOT IN (
                        SELECT Sender FROM Invites WHERE Recipient = (SELECT UserName FROM Users WHERE UserID = ?)
                    )
                    GROUP BY u.UserID
                    ORDER BY shared_count DESC
                    LIMIT ? OFFSET ?
                """
                self.cursor.execute(sql, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, limit, offset))
                return self.cursor.fetchall()
            except Exception as e:
                print(e)
                return []
            finally:
                self.close_db()

    def clean_dead_users(self):
        with self.lock:
            self.open_db()
            try:
                sql = "SELECT UserID FROM Users WHERE FinishedReg < 3 AND LastConnected < datetime('now', '-30 minutes')"
                result = self.cursor.execute(sql).fetchall()
                print(result)
                for id in result:
                    sql = "DELETE FROM UserHobbies WHERE UserID = ?"
                    self.cursor.execute(sql, (id[0],))
                sql = "DELETE FROM Users WHERE FinishedReg < 3 AND LastConnected < datetime('now', '-30 minutes')"
                self.cursor.execute(sql)
                self.commit()
                count = self.cursor.rowcount
                if count > 0:
                    print(f"[Cleanup] Deleted {count} unfinished registration(s).")
            except Exception as e:
                print(f"[Cleanup Error] {e}")
            finally:
                self.close_db()

def mailboxes_worker(username, sock, dh_key, IV):
    while True:
        msg = mailboxes[username].get()
        if msg is None:
            break
        send_with_AES(sock, msg, dh_key, IV)


def mailboxes_worker_udp(username, sock, dh_key, IV):
    global udp_addr_map_reverse
    while True:
        msg = mailboxes_udp[username].get()
        if msg is None:
            break
        while username not in udp_addr_map_reverse:
            time.sleep(0.01)
        cipher = AES.new(dh_key, AES.MODE_CBC, IV.encode())
        encrypted = cipher.encrypt(pad(msg.encode(), AES.block_size))
        sock.sendto(encrypted, udp_addr_map_reverse[username])
        print("sent")


def handle_client_udp():
    while True:
        try:
            raw, addr = udp_sock.recvfrom(65535)
            username = udp_addr_map.get(addr)
            if not username:
                print(f"Unknown addr {addr}, trying all keys...")
                for uname, key in udp_keys.items():
                    try:
                        cipher = AES.new(key, AES.MODE_CBC, IV.encode())
                        data = unpad(cipher.decrypt(raw), AES.block_size).decode()
                        udp_addr_map[addr] = uname
                        udp_addr_map_reverse[uname] = addr
                        username = uname
                        break
                    except Exception as e:
                        print(f"Key trial failed for {uname}: {e}")
                        continue
                if not username:
                    print("Could not identify sender, skipping")
                    continue
            key = udp_keys[username]
            cipher = AES.new(key, AES.MODE_CBC, IV.encode())
            data = unpad(cipher.decrypt(raw), AES.block_size).decode()
            splited_data = data.split("|")
            if splited_data[0] == "CATU":
                with mailboxes_lock:
                    if splited_data[1] in mailboxes and splited_data[1] in mailboxes_udp:
                        mailboxes_udp[splited_data[1]].put(f"GAFU|{username}|{splited_data[2]}")
                    else:
                        print(f"Recipient {splited_data[1]} not in mailboxes_udp")
            elif splited_data[0] == "VDFU":
                with mailboxes_lock:
                    if splited_data[1] in mailboxes_udp:
                        mailboxes_udp[splited_data[1]].put(f"GVST|{username}|{splited_data[2]}|{splited_data[3]}|{splited_data[4]}|{splited_data[5]}")
                    else:
                        print(f"Recipient {splited_data[1]} not in mailboxes_udp")
        except Exception as e:
            print(f"UDP error: {e}")




db = DataBase()
def handle_client(sock, addr):
    global db
    global IV
    global mailboxes
    global mailboxes_lock
    global whos_in_call
    global udp_addr_map
    global udp_keys
    generated_dh = False
    user_id = ""
    username = ""
    offset = 0
    limit = 20
    did_udp_thread_start = False
    pfp_directory_path = r"D:\Cyber Harel\YB_Project\logic\profilepicturesofusers"
    if not generated_dh:
        dh_key = diffie_hellman(sock)
        generated_dh = True
    while True:
        data = recv_with_AES(sock, dh_key, IV).decode("utf-8")
        splited_data = data.split("|")
        if data == "":
            pass
        elif splited_data[0] == "REGQ":
            hashed, salt = hashing_for_sign_up(splited_data[2])
            result = db.insert_new_user(splited_data[1], hashed, salt)
            if result[0] == "GOOD":
                user_id = result[1]
                username = splited_data[1]
                send_with_AES(sock, "REGG|", dh_key, IV)
            else:
                result = db.check_if_available(splited_data[1], hashed, salt)
                print(result)
                if result[0] == "GOOD":
                    user_id = result[1]
                    username = splited_data[1]
                    send_with_AES(sock, "REGG|", dh_key, IV)
                else:
                    send_with_AES(sock, "REGN|", dh_key, IV)
        elif splited_data[0] == "LOGQ":
            result = db.for_login(splited_data[1], splited_data[2])
            if result[0] == "BAD":
                send_with_AES(sock, "LOGN|", dh_key, IV)
            elif result[0] == "SEMI":
                username = splited_data[1]
                user_id = result[1][1]
                if result[1][0] == 1:
                    send_with_AES(sock, "LOGO|", dh_key, IV)
                else:
                    send_with_AES(sock, "LOGT|", dh_key, IV)
            else:
                if result[1] is None:
                    send_with_AES(sock, "LOGN|", dh_key, IV)
                else:
                    user_id = result[1][0]
                    username = splited_data[1]
                    send_with_AES(sock ,"STSK|", dh_key, IV)
                    keys = db.get_keys(username)
                    print(f"Keys are: {keys}")
                    for key in keys:
                        send_with_AES(sock, f"KEYS|{key[0]}|{key[1]}", dh_key, IV)
                    db.delete_keys(username)
                    with mailboxes_lock:
                        mailboxes[username] = queue.Queue()
                    out_thread = threading.Thread(target=mailboxes_worker,args=(username, sock, dh_key, IV),daemon=True)
                    out_thread.start()
                    invites = db.get_invites_offline(username)
                    print(f"offline invites for {username}: {invites}")
                    for i in invites:
                        pfpname = db.get_pfp_name_by_username(i[0])
                        file_path = os.path.join(pfp_directory_path, pfpname[0][0])
                        with open(file_path, "rb") as file:
                            content = file.read()
                        based_content = base64.b64encode(content).decode('utf-8')
                        send_with_AES(sock, f"INVR|{i[0]}|{based_content}|{i[1]}", dh_key, IV)
                    db.clear_offline_invites(username)
                    chats = db.get_chats(username)
                    for i in chats:
                        pfpname = db.get_pfp_name_by_username(i[0])
                        file_path = os.path.join(pfp_directory_path, pfpname[0][0])
                        with open(file_path, "rb") as file:
                            content = file.read()
                        based_content = base64.b64encode(content).decode('utf-8')
                        send_with_AES(sock, f"CHAT|{i[0]}|{based_content}|{""}", dh_key, IV)
                        msgs = db.get_messages_between(username, i[0])
                        for msg in msgs:
                            if msg[0] == username:
                                print(msg[0])
                                print(i[0])
                                send_with_AES(sock, f"GMFF|{i[0]}|{msg[1]}|{msg[2]}|0", dh_key, IV)
                            else:
                                send_with_AES(sock, f"GMFF|{i[0]}|{msg[1]}|{msg[2]}|1", dh_key, IV)
                    with mailboxes_lock:
                        for i in chats:
                            if whos_in_call.get(i[0]) == username:
                                send_with_AES(sock, f"HIIC|{i[0]}", dh_key, IV)
                            else:
                                send_with_AES(sock, f"HINC|{i[0]}", dh_key, IV)
                    user_id = result[1][0]
                    username = splited_data[1]
                    udp_keys[username] = dh_key
                    pfp = db.get_pfp_name_by_username(username)
                    file_path = os.path.join(pfp_directory_path, pfp[0][0])
                    with open(file_path, "rb") as file:
                        content = file.read()
                    based_content = base64.b64encode(content).decode('utf-8')
                    send_with_AES(sock, f"LOGG|{based_content}", dh_key, IV)
        elif splited_data[0] == "HOBB":
            result = db.check_if_hobbies(user_id, splited_data[1].split("~"))
            if result:
                send_with_AES(sock, "HOOK|", dh_key, IV)
            else:
                send_with_AES(sock, "HONO|", dh_key, IV)
        elif splited_data[0] == "PFPS":
            if splited_data[1] == "DEFAULT":
                result = db.check_if_pfp(user_id, "defaultpfp.png")
                if result:
                    send_with_AES(sock, "PFPF|", dh_key, IV)
                else:
                    send_with_AES(sock, "PFPW|", dh_key, IV)
            else:
                try:
                    file_name = f"{user_id}pfp.{splited_data[1]}"
                    result = db.check_if_pfp(user_id, file_name)
                    if result:
                        img_bytes = base64.b64decode(splited_data[2])
                        file_path = os.path.join(pfp_directory_path, file_name)
                        with open(file_path, 'wb') as file:
                            file.write(img_bytes)
                        send_with_AES(sock, "PFPF|", dh_key, IV)
                    else:
                        send_with_AES(sock, "PFPW|", dh_key, IV)
                except Exception as e:
                    print(f"Error processing image: {e}")
                    send_with_AES(sock, "PFPB|", dh_key, IV)
        elif splited_data[0] == "GDFS":
            print(f"GDFS received, user_id={user_id}, offset={offset}")
            data = db.get_users_by_shared_hobbies(user_id, limit, offset)
            if not data:
                send_with_AES(sock, "NOMU|", dh_key, IV)
            else:
                data_to_send = "DFSC|"
                for i in data:
                    data_to_send += f"{i[0]}~{i[1]}~{i[2]}~{i[3]}~{i[4]}|"
                print(data_to_send)
                send_with_AES(sock, data_to_send[:-1], dh_key, IV)
                offset += limit
        elif splited_data[0] == "GPOF":
            file_path = os.path.join(pfp_directory_path, splited_data[1])
            with open(file_path, "rb") as file:
                content = file.read()
            based_content = base64.b64encode(content).decode('utf-8')
            send_with_AES(sock, f"ROUP|{based_content}", dh_key, IV)
        elif splited_data[0] == "INVI":
            print(f"INVI received - sender username: '{username}', target: '{splited_data[1]}'")
            pfpname = db.get_pfp_name_by_username(username)
            print(f"pfpname result: {pfpname}")
            file_path = os.path.join(pfp_directory_path, pfpname[0][0])
            with open(file_path, "rb") as file:
                content = file.read()
            based_content = base64.b64encode(content).decode('utf-8')
            with mailboxes_lock:
                print(f"mailboxes keys: {list(mailboxes.keys())}")
                if splited_data[1] in mailboxes:
                    print("target is online, putting in mailbox")
                    mailboxes[splited_data[1]].put(f"INVR|{username}|{based_content}|{splited_data[2]}")
                else:
                    print("target is offline, storing in DB")
                    db.add_invite(username, splited_data[1], splited_data[2])
        elif splited_data[0] == "INVA":
            db.add_chat(splited_data[1], username)
            pfpname = db.get_pfp_name_by_username(username)
            file_path = os.path.join(pfp_directory_path, pfpname[0][0])
            with open(file_path, "rb") as file:
                content = file.read()
            based_content = base64.b64encode(content).decode('utf-8')
            with mailboxes_lock:
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"CHAT|{username}|{based_content}|{splited_data[2]}")
                else:
                    db.insert_new_key(username, splited_data[1], splited_data[2])
        elif splited_data[0] == "MSFU":
            timestamp = db.insert_new_message(username, splited_data[1], splited_data[2])
            send_with_AES(sock, f"TSFS|{timestamp}|{splited_data[1]}|", dh_key, IV)
            with mailboxes_lock:
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"USAM|{username}|{splited_data[2]}|{timestamp}")
        elif splited_data[0] == "SAAC":
            if not did_udp_thread_start:
                with mailboxes_lock:
                    mailboxes_udp[username] = queue.Queue()
                udp_thread = threading.Thread(target=mailboxes_worker_udp,args=(username, udp_sock, udp_keys[username], IV), daemon=True)
                udp_thread.start()
                did_udp_thread_start = True
            my_pfp = db.get_pfp_name_by_username(username)
            file_path = os.path.join(pfp_directory_path, my_pfp[0][0])
            with open(file_path, "rb") as file:
                content = file.read()
            based_content = base64.b64encode(content).decode('utf-8')
            other_pfp = db.get_pfp_name_by_username(splited_data[1])
            file_path = os.path.join(pfp_directory_path, other_pfp[0][0])
            with open(file_path, "rb") as file:
                content = file.read()
            based_content_second = base64.b64encode(content).decode('utf-8')
            with mailboxes_lock:
                whos_in_call[username] = splited_data[1]
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"SPUC|{username}|{based_content}|{based_content_second}|{splited_data[2]}")
        elif splited_data[0] == "CASU":
            if not did_udp_thread_start:
                with mailboxes_lock:
                    mailboxes_udp[username] = queue.Queue()
                udp_thread = threading.Thread(target=mailboxes_worker_udp, args=(username, udp_sock, udp_keys[username], IV), daemon=True)
                udp_thread.start()
                did_udp_thread_start = True
            with mailboxes_lock:
                whos_in_call[username] = splited_data[1]
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"UATC|{splited_data[1]}|{splited_data[2]}")
        elif splited_data[0] == "CBUA":
            if not did_udp_thread_start:
                with mailboxes_lock:
                    mailboxes_udp[username] = queue.Queue()
                udp_thread = threading.Thread(target=mailboxes_worker_udp,args=(username, udp_sock, udp_keys[username], IV), daemon=True)
                udp_thread.start()
                did_udp_thread_start = True
            with mailboxes_lock:
                whos_in_call[username] = splited_data[1]
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"URTC|{splited_data[2]}")
        elif splited_data[0] == "IHTC":
            with mailboxes_lock:
                whos_in_call[username] = ""
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put("UHTC|")
        elif splited_data[0] == "IHUT":
            with mailboxes_lock:
                whos_in_call[username] = ""
                if splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put(f"UHUT|{username}")
        elif splited_data[0] == "DION":
            with mailboxes_lock:
                if splited_data[1] in whos_in_call and splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put("UTOD|")
        elif splited_data[0] == "DOFF":
            with mailboxes_lock:
                if splited_data[1] in whos_in_call and splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put("TDOF|")
        elif splited_data[0] == "ITOC":
            with mailboxes_lock:
                if splited_data[1] in whos_in_call and splited_data[1] in mailboxes:
                    mailboxes[splited_data[1]].put("UTOC|")
        elif splited_data[0] == "EXIT":
            with mailboxes_lock:
                if username in whos_in_call:
                    del whos_in_call[username]
                if username in mailboxes.keys():
                    mailboxes[username].put(None)
                    del mailboxes[username]
            return

def main():
    global db
    global udp_sock
    db.setup_db()

    cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
    cleanup_thread.start()

    threads = []
    server_socket = socket.socket()

    server_socket.bind(('0.0.0.0', 5000))

    server_socket.listen(10)

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    threading.Thread(target=handle_client_udp, daemon=True).start()

    i = 1
    while True:
        print('\nMain thread: before accepting ...')
        cli_sock, cli_address = server_socket.accept()
        t = threading.Thread(target=handle_client, args=(cli_sock, cli_address))
        t.start()
        i += 1
        threads.append(t)
        if i > 100000000:  # for tests change it to 4
            print('\nMain thread: going down for maintenance')
            break

    all_to_die = True
    print('Main thread: waiting to all clients to die')
    for t in threads:
        t.join()
    server_socket.close()
    print('Bye ..')








if __name__ == '__main__':
    main()