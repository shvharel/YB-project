import base64
import os.path

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QSize, QTimer, Qt, QThread, QObject, Signal, Slot, QRect
from PySide6.QtWidgets import QPushButton, QLineEdit, QStackedWidget, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QMessageBox, QMainWindow, QCheckBox, QFileDialog, QLabel, QScrollArea, QDialog
import ui.resources_rc
import socket
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QImage
from tcp_by_size import recv_by_size, send_with_size
import secrets, hashlib
from TCP_AES import send_with_AES, recv_with_AES
from widgets.bell_button import BellButton
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pathlib import Path
from widgets.chat_bubble import ChatBubble, DateSeparator
import pyaudio
import queue
from threading import Thread
import cv2
import numpy as np
import time
from PySide6.QtCore import Signal as pyqtSignal

icons_path = r"D:\Cyber Harel\YB_Project\icons"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1000



class Worker(QObject):
    response_login = Signal(bool, str)
    response_signup = Signal(bool)
    response_hobbies = Signal(bool)
    response_pfp = Signal(bool)
    response_pfp_bug = Signal()
    response_login_steps = Signal(int)
    finished = Signal()
    response_after_login = Signal(list)
    response_after_user_pfp = Signal(str)
    response_no_more_users = Signal(str)
    request_for_chat = Signal(str, str, str)
    insert_new_chat = Signal(str, str, str)
    response_keys = Signal(str, str)
    new_message = Signal(str, str, str)
    timestamp_for_message = Signal(str, str)
    set_keys = Signal()
    get_messages_from_offline = Signal(str, str, str, str)
    show_pop_up = Signal(str, str, str)
    response_user_pickedup = Signal(str, str)
    got_audio = Signal(str, str)
    user_rejoined = Signal()
    user_hanged_up = Signal()
    user_hanged_up_too = Signal(str)
    get_users_in_call = Signal(str)
    enter_users_in_call = Signal(str)
    other_deafened = Signal()
    other_undeafened = Signal()
    video_stream = Signal(str, str, str, str, str)
    user_turned_camera_off = Signal()

    def __init__(self, ip, port, diffiehellmankey, iv, sock, udp_sock,parent=None):
        super().__init__(None)
        self.ip = ip
        self.port = port
        self.diffiehellmankey = diffiehellmankey
        self.iv = iv
        self.sock = sock
        self.udp_sock = udp_sock

    @Slot()
    def run(self):
        i = 0
        Thread(target=self.run_udp, daemon=True).start()
        while True:
            try:
                data = recv_with_AES(self.sock, self.diffiehellmankey, self.iv).decode("utf-8")
                if not data:
                    break
                splited_data = data.split("|")
                print(splited_data[0])
                if splited_data[0] == "REGG":
                    self.response_signup.emit(True)
                elif splited_data[0] == "REGN":
                    self.response_signup.emit(False)
                elif splited_data[0] == "LOGG":
                    self.response_login.emit(True, splited_data[1])
                elif splited_data[0] == "LOGN":
                    self.response_login.emit(False, "")
                elif splited_data[0] == "LOGO":
                    self.response_login_steps.emit(1)
                elif splited_data[0] == "LOGT":
                    self.response_login_steps.emit(2)
                elif splited_data[0] == "HOOK":
                    self.response_hobbies.emit(True)
                elif splited_data[0] == "HONO":
                    self.response_hobbies.emit(False)
                elif splited_data[0] == "PFPF":
                    self.response_pfp.emit(True)
                elif splited_data[0] == "PFPW":
                    self.response_pfp.emit(False)
                elif splited_data[0] == "PFPB":
                    self.response_pfp.emit()
                elif splited_data[0] == "DFSC":
                    self.response_after_login.emit(splited_data[1:])
                elif splited_data[0] == "ROUP":
                    self.response_after_user_pfp.emit(splited_data[1])
                elif splited_data[0] == "NOMU":
                    self.response_no_more_users.emit("There are no more users!")
                elif splited_data[0] == "INVR":
                    self.request_for_chat.emit(splited_data[1], splited_data[2], splited_data[3])
                elif splited_data[0] == "CHAT":
                    self.insert_new_chat.emit(splited_data[1], splited_data[2], splited_data[3])
                elif splited_data[0] == "KEYS":
                    self.response_keys.emit(splited_data[1], splited_data[2])
                elif splited_data[0] == "USAM":
                    self.new_message.emit(splited_data[1], splited_data[2], splited_data[3])
                elif splited_data[0] == "TSFS":
                    self.timestamp_for_message.emit(splited_data[1], splited_data[2])
                elif splited_data[0] == "STSK":
                    self.set_keys.emit()
                elif splited_data[0] == "GMFF":
                    self.get_messages_from_offline.emit(splited_data[1], splited_data[2], splited_data[3], splited_data[4])
                elif splited_data[0] == "SPUC":
                    self.show_pop_up.emit(splited_data[1], splited_data[2], splited_data[3])
                elif splited_data[0] == "UATC":
                    self.response_user_pickedup.emit(splited_data[1], splited_data[2])
                elif splited_data[0] == "URTC":
                    self.user_rejoined.emit()
                elif splited_data[0] == "UHTC":
                    self.user_hanged_up.emit()
                elif splited_data[0] == "UHUT":
                    self.user_hanged_up_too.emit(splited_data[1])
                elif splited_data[0] == "HIIC":
                    self.get_users_in_call.emit(splited_data[1])
                elif splited_data[0] == "HINC":
                    self.enter_users_in_call.emit(splited_data[1])
                elif splited_data[0] == "UTOD":
                    self.other_deafened.emit()
                elif splited_data[0] == "TDOF":
                    self.other_undeafened.emit()
                elif splited_data[0] == "UTOC":
                    self.user_turned_camera_off.emit()
            except OSError:
                break
            except Exception as e:
                print(f"Error:{e}")
                break

        self.sock.close()
        self.finished.emit()

    def run_udp(self):
        while True:
            try:
                raw, addr = self.udp_sock.recvfrom(65535)
                cipher = AES.new(self.diffiehellmankey, AES.MODE_CBC, self.iv.encode())
                data = unpad(cipher.decrypt(raw), AES.block_size).decode()
                print(data)
                splited_data = data.split("|")
                if splited_data[0] == "GAFU":
                    self.got_audio.emit(splited_data[1], splited_data[2])
                elif splited_data[0] == "GVST":
                    self.video_stream.emit(splited_data[1], splited_data[2], splited_data[3], splited_data[4], splited_data[5])
            except Exception as e:
                #print(f"UDP error: {e}")
                pass





class MainController(QMainWindow):
    my_video_signal = Signal(QPixmap)
    def __init__(self):
        super().__init__()
        Loader = QUiLoader()
        ui_file = QFile("ui/MainWindow.ui")
        ui_file.open(QFile.ReadOnly)
        self.main = Loader.load(ui_file)
        ui_file.close()

        self.setCentralWidget(self.main)

        self.stacked = self.main.findChild(QStackedWidget, "stackedWidget")

        self.setCentralWidget(self.main)

        self.start = self.load_ui("ui/Start2.ui")
        self.login = self.load_ui("ui/Login2.ui")
        self.signup = self.load_ui("ui/Signup.ui")
        self.hobbies = self.load_ui("ui/hobbies.ui")
        self.upload_pfp_signup = self.load_ui("ui/profilpicforsignup.ui")
        self.scroll = self.load_ui("ui/scroll.ui")
        self.notifications = self.load_ui("ui/notifications.ui")
        self.chat_hub = self.load_ui("ui/Chathub.ui")
        self.chat = self.load_ui("ui/chat.ui")
        self.call = self.load_ui("ui/audiocall.ui")
        self.callpopup = self.load_ui("ui/callpopup.ui")
        self.audio_call_alone = self.load_ui("ui/audiocallalone.ui")
        #self.video_call = self.load_ui("ui/videocall.ui")
        #self.video_call_alone = self.load_ui("ui/videocallalone.ui")


        scroll_contents = self.notifications.findChild(QWidget, "scrollcontents")
        self.invite_list_layout = scroll_contents.layout()

        scroll_contents = self.chat_hub.findChild(QWidget, "scrollcontents")
        self.chat_hub_list_layout = scroll_contents.layout()

        self.resize(self.main.size())

        self.stacked.addWidget(self.start)
        self.stacked.addWidget(self.login)
        self.stacked.addWidget(self.signup)
        self.stacked.addWidget(self.hobbies)
        self.stacked.addWidget(self.upload_pfp_signup)
        self.stacked.addWidget(self.scroll)
        self.stacked.addWidget(self.notifications)
        self.stacked.addWidget(self.chat_hub)
        self.stacked.addWidget(self.chat)
        self.stacked.addWidget(self.call)
        self.stacked.addWidget(self.audio_call_alone)
        #self.stacked.addWidget(self.video_call)
        #self.stacked.addWidget(self.video_call_alone)


        self.TheMainThread = None
        self.TheWorker = None

        self.pfpsize = 300
        self.default_pfp_path = r"D:\Cyber Harel\YB_Project\icons\defaultpfp.png"

        self.show()
        print("size:", self.main.size())

        self.is_visible_login = False
        self.is_visible_signup = False
        self.generated_dh = False
        self.DiffieHellmankey = None
        self.IV = 'hefuhrgjhsdfirps'
        for child in self.scroll.findChildren(QPushButton):
            print(child.objectName())

        chat_contents = self.chat.findChild(QWidget, "scrollcontents")
        self.chat_layout = chat_contents.layout()
        self.chat_scroll = self.chat.findChild(QScrollArea, "scrollArea")
        self.last_message_date = None

        self.FirstLoginButton = self.start.findChild(QPushButton, "LogInButton")
        self.eyeLogin = self.login.findChild(QPushButton, "eye")
        self.eyeSignup = self.signup.findChild(QPushButton, "eye")
        self.FirstSignupButton = self.start.findChild(QPushButton, "SignUpButton")
        self.SecondLoginButton = self.login.findChild(QPushButton, "loginbutton")
        self.SecondSignupButton = self.signup.findChild(QPushButton, "signupbutton")
        self.changesignup = self.login.findChild(QPushButton, "signupbutton")
        self.changelogin = self.signup.findChild(QPushButton, "loginbutton_3")
        self.confirm_button = self.hobbies.findChild(QPushButton, "confirmbutton")
        self.continue_button = self.upload_pfp_signup.findChild(QPushButton, "continuebutton")
        self.upload_button = self.upload_pfp_signup.findChild(QPushButton, "uploadbutton")
        self.next_button = self.scroll.findChild(QPushButton, "nextbutton")
        self.invite_button = self.scroll.findChild(QPushButton, "invitebutton")
        self.chat_button = self.scroll.findChild(QPushButton, "chatbutton")
        self.bell_button = self.scroll.findChild(BellButton, "bellbutton")
        self.send_button = self.chat.findChild(QPushButton, "sendbutton")
        self.phone_button = self.chat.findChild(QPushButton, "phonebutton")
        self.video_button = self.chat.findChild(QPushButton, "videobutton")
        self.hangup_button = self.call.findChild(QPushButton, "hangupbutton")
        self.video_call_button = self.call.findChild(QPushButton, "videobutton")
        self.deafen_button = self.call.findChild(QPushButton, "deafenbutton")
        self.mic_button = self.call.findChild(QPushButton, "micbutton")
        self.hangup_button_alone = self.audio_call_alone.findChild(QPushButton, "hangupbutton")
        self.video_call_button_alone = self.audio_call_alone.findChild(QPushButton, "videobutton")
        self.deafen_button_alone = self.audio_call_alone.findChild(QPushButton, "deafenbutton")
        self.mic_button_alone = self.audio_call_alone.findChild(QPushButton, "micbutton")
        self.back_button = self.chat.findChild(QPushButton, "backbutton")
        self.scroll_button = self.chat_hub.findChild(QPushButton, "scrollbutton")

        self.password_login = self.login.findChild(QLineEdit, "Password")
        self.password_signup = self.signup.findChild(QLineEdit, "Password")
        self.login_username = self.login.findChild(QLineEdit, "Username")
        self.signup_username = self.signup.findChild(QLineEdit, "Username")
        self.login_ip = self.login.findChild(QLineEdit, "IP_line")
        self.signup_ip = self.signup.findChild(QLineEdit, "IP_line")
        self.pfp_signup = self.upload_pfp_signup.findChild(QLabel, "pfp")
        self.pfp_scroll = self.scroll.findChild(QLabel, "pfp")
        self.user_scroll = self.scroll.findChild(QLabel, "userusername")
        self.hobbies_scroll = self.scroll.findChild(QLabel, "hobbies")
        self.message_chat = self.chat.findChild(QLineEdit, "lineEdit")
        self.username_chat = self.chat.findChild(QLabel, "username")
        self.pfp_chat = self.chat.findChild(QLabel, "pfp")
        self.my_pfp_call = self.call.findChild(QLabel, "mypfp")
        self.second_user_pfp_call = self.call.findChild(QLabel, "seconduserpfp")
        self.pfp_call_alone = self.audio_call_alone.findChild(QLabel, "mypfp")
        self.text_alone = self.audio_call_alone.findChild(QLabel, "waitingforuser")


        self.checkbox = self.hobbies.findChildren(QCheckBox)

        self.FirstLoginButton.clicked.connect(lambda: self.stacked.setCurrentWidget(self.login))
        self.FirstSignupButton.clicked.connect(lambda: self.stacked.setCurrentWidget(self.signup))
        self.changelogin.clicked.connect(self.Changing_to_login)
        self.changesignup.clicked.connect(self.Changing_to_signup)
        self.eyeLogin.clicked.connect(self.ShowPasswordLogIn)
        self.eyeSignup.clicked.connect(self.ShowPasswordSignUp)
        self.SecondLoginButton.clicked.connect(self.OnLogin)
        self.SecondSignupButton.clicked.connect(self.OnSignup)
        self.confirm_button.clicked.connect(self.on_confirm_hobbies)
        self.continue_button.clicked.connect(self.on_continue_pfp)
        self.upload_button.clicked.connect(self.upload_pfp)
        self.next_button.clicked.connect(self.on_next)
        self.invite_button.clicked.connect(self.on_invite)
        self.bell_button.clicked.connect(self.on_bell)
        self.chat_button.clicked.connect(lambda : self.stacked.setCurrentWidget(self.chat_hub))
        self.send_button.clicked.connect(self.on_send)
        self.phone_button.clicked.connect(self.on_call)
        self.hangup_button.clicked.connect(self.on_hangup)
        self.deafen_button.clicked.connect(self.on_deafen)
        self.mic_button.clicked.connect(self.on_mute)
        self.hangup_button_alone.clicked.connect(self.on_hangup_alone)
        self.deafen_button_alone.clicked.connect(self.on_deafen)
        self.mic_button_alone.clicked.connect(self.on_mute)
        self.video_button.clicked.connect(self.on_video)
        self.video_call_button.clicked.connect(self.on_camera)
        self.back_button.clicked.connect(lambda: self.stacked.setCurrentWidget(self.chat_hub))
        self.scroll_button.clicked.connect(self.on_scroll)

        self.my_pfp_call.setFixedSize(200, 200)
        self.second_user_pfp_call.setFixedSize(200, 200)
        self.my_pfp_call.setAlignment(Qt.AlignCenter)
        self.second_user_pfp_call.setAlignment(Qt.AlignCenter)
        self.pfp_call_alone.setFixedSize(200, 200)
        self.pfp_call_alone.setAlignment(Qt.AlignCenter)


        self.selected_image_path = ''
        self.is_pfp_default = True
        self.list_of_users = []
        self.first = True
        self.scroll_pfp = QPixmap()
        self.current_chat_user = ""
        self.dh_key_for_each_user = {}
        self.pending_dh = {}
        self.password = ""
        self.username = ""
        self.pending_sent_message = {}
        self.user_in_chat = False
        self.message_buffer = {}
        self.current_user_pfp = ""
        self.audio_running = False
        self.playback_queue = queue.Queue()
        self.p = pyaudio.PyAudio()
        self.my_pfp = ""
        self.is_mute = False
        self.is_deafen = False
        self.person_in_call = ""
        self.person_in_call_pfp = ""
        self.is_person_in_call = {}
        self.still_in_call = False
        self.other_deafen = False
        self.is_video = False
        self.local_cap = None
        self.my_video_signal.connect(lambda pix: self.my_pfp_call.setPixmap(pix.scaled(self.my_pfp_call.size(), Qt.KeepAspectRatio)))
        self.last_user = []

        self.sock = socket.socket()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_udp_addr = None
        self.video_chunks = {}

    @Slot()
    def response_user_turned_camera_off(self):
        self.person_in_call_pfp.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))

    @Slot(str, str, str, str, str)
    def response_got_video(self, sender, frame_id, idx, total, chunk):
        try:
            idx = int(idx)
            total = int(total)
            if frame_id not in self.video_chunks:
                self.video_chunks[frame_id] = {}
            self.video_chunks[frame_id][idx] = chunk

            if len(self.video_chunks[frame_id]) == total:
                full_data = "".join(self.video_chunks[frame_id][i] for i in range(total))
                del self.video_chunks[frame_id]
                self.display_video_frame(sender, full_data)
            if len(self.video_chunks) > 10:
                oldest = next(iter(self.video_chunks))
                del self.video_chunks[oldest]
        except Exception as e:
            print(f"Video error: {e}")

    @Slot()
    def response_user_undeafend(self):
        self.other_deafen = False

    @Slot()
    def response_user_deafend(self):
        self.other_deafen = True

    @Slot(str)
    def response_dont_in_call(self, username):
        self.is_person_in_call[username] = False

    @Slot(str)
    def response_do_in_call(self, username):
        self.is_person_in_call[username] = True


    @Slot(str)
    def response_user_hanged_up_too(self, username):
        self.is_person_in_call[username] = False
        self.other_deafen = False


    @Slot()
    def response_user_hanged_up(self):
        global icons_path
        self.audio_running = False
        self.is_person_in_call[self.person_in_call] = False
        self.pfp_call_alone.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
        file_path = os.path.join(icons_path, "mute.png" if self.is_mute else "mic.png")
        self.mic_button_alone.setIcon(QIcon(file_path))
        file_path = os.path.join(icons_path, "deafen.png" if self.is_deafen else "headphones.png")
        self.deafen_button_alone.setIcon(QIcon(file_path))
        self.text_alone.setText(f"Waiting for {self.person_in_call} to pickup")
        self.other_deafen = False
        self.stacked.setCurrentWidget(self.audio_call_alone)

    @Slot()
    def response_user_rejoined(self):
        global icons_path
        if self.audio_running:
            return
        self.audio_running = True
        self.is_person_in_call[self.person_in_call] = True
        self.second_user_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.person_in_call_pfp, 70))
        self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
        if self.is_deafen:
            file_path = os.path.join(icons_path, "deafen.png")
            self.deafen_button.setIcon(QIcon(file_path))
        if self.is_mute:
            file_path = os.path.join(icons_path, "mute.png")
            self.mic_button.setIcon(QIcon(file_path))
        if self.audio_running:
            Thread(target=self.capture_audio).start()
            Thread(target=self.playback_audio).start()
        Thread(target=self.capture_video).start()
        if self.is_video:
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button.setIcon(QIcon(file_path))
        self.stacked.setCurrentWidget(self.call)

    @Slot(str, str)
    def response_got_audio(self, sender ,data):
            try:
                raw = base64.b64decode(data)
                iv, encrypted = raw[:16], raw[16:]
                cipher = AES.new(self.dh_key_for_each_user[sender], AES.MODE_CBC, iv)
                chunk = unpad(cipher.decrypt(encrypted), AES.block_size)
                self.playback_queue.put(chunk)
            except Exception as e:
                print(f"Decryption error: {e}")


    @Slot(str, str)
    def response_pickingup(self, other_user, my_pfp):
        self.is_person_in_call[self.person_in_call] = True
        self.audio_running = True
        self.second_user_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.person_in_call_pfp, 70))
        self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
        Thread(target=self.capture_audio).start()
        Thread(target=self.playback_audio).start()
        Thread(target=self.capture_video).start()
        if self.is_video:
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button.setIcon(QIcon(file_path))
        self.stacked.setCurrentWidget(self.call)



    @Slot(str, str, str)
    def user_called_you(self, caller, his_pfp, my_pfp):
        self.callpopup = self.load_ui("ui/callpopup.ui")
        dialog = QDialog(self.main)
        dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.callpopup)
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(his_pfp))
        self.is_person_in_call[caller] = True
        self.callpopup.findChild(QLabel, "pfp").setPixmap(self.get_perfect_circular_pixmap_from_pixmap(pixmap, 70))
        self.callpopup.findChild(QLabel, "username").setText(caller)
        self.callpopup.findChild(QPushButton, "pickupbutton").clicked.connect(dialog.accept)
        self.callpopup.findChild(QPushButton, "hangupbutton").clicked.connect(dialog.reject)

        result = dialog.exec()

        if result == QDialog.Accepted:
            send_with_AES(self.sock, f"CASU|{caller}|{his_pfp}", self.DiffieHellmankey, self.IV)
            self.current_chat_user = caller
            self.audio_running = True
            self.is_person_in_call[caller] = True
            self.still_in_call = True
            self.second_user_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(pixmap, 70))
            self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
            self.stacked.setCurrentWidget(self.call)
            Thread(target=self.capture_audio).start()
            Thread(target=self.playback_audio).start()
            Thread(target=self.capture_video).start()
            self.person_in_call = caller
            self.person_in_call_pfp = pixmap
        else:
            send_with_AES(self.sock, f"CDEC|{caller}", self.DiffieHellmankey, self.IV)



    @Slot(str, str, str, str)
    def response_msgs_offline(self, sender, data, timestamp, checker):
        if sender not in self.dh_key_for_each_user:
            return
        try:
            key = self.dh_key_for_each_user[sender]
            raw = base64.b64decode(data)
            iv = raw[:16]
            encrypted = raw[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            message = unpad(cipher.decrypt(encrypted), AES.block_size).decode()
            if checker == "0":
                self.message_buffer.setdefault(sender, []).append((message, True, timestamp))
            else:
                self.message_buffer.setdefault(sender, []).append((message, False, timestamp))
        except Exception as e:
            print(f"Decryption error: {e}")


    @Slot()
    def response_set_keys(self):
        self.username = self.login_username.text().strip()
        self.password = self.password_login.text().strip()
        path = Path(f"{self.username}_keys.enc")
        try:
            raw = path.read_bytes()
            salt = raw[:16]
            iv = raw[16:32]
            encrypted = raw[32:]
            storage_key = hashlib.pbkdf2_hmac('sha256', self.password.encode(), salt, 100000)
            cipher = AES.new(storage_key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
            data = json.loads(decrypted.decode())
            self.dh_key_for_each_user = {k: bytes.fromhex(v) for k, v in data["dh_keys"].items()}
            self.pending_dh = {k: int(v) for k, v in data["pending_dh"].items()}
        except Exception as e:
            print(f"Failed to load keys: {e}")
    @Slot(str, str)
    def response_timestamp(self, timestamp, username):
        if username in self.pending_sent_message:
            message = self.pending_sent_message.pop(username)
            self.display_message(message, True, timestamp)

    @Slot(str, str, str)
    def server_response_new_message(self, username, data, timestamp):
        if username not in self.dh_key_for_each_user:
            return
        try:
            key = self.dh_key_for_each_user[username]
            raw = base64.b64decode(data)
            iv = raw[:16]
            encrypted = raw[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            message = unpad(cipher.decrypt(encrypted), AES.block_size).decode()
            if self.user_in_chat:
                if self.current_chat_user == username:
                    self.display_message(message, False, timestamp)
            else:
                self.message_buffer.setdefault(username, []).append((message, False, timestamp))
        except Exception as e:
            print(f"Decryption error: {e}")


    @Slot(str, str)
    def server_response_new_keys(self, B, username):
        if username not in self.pending_dh:
            return
        key = pow(int(B), self.pending_dh[username], self.generate_prime())
        shared_secret_bytes = key.to_bytes((key.bit_length() + 7) // 8, 'big')
        self.dh_key_for_each_user[username] = hashlib.sha256(shared_secret_bytes).digest()


    @Slot(str, str, str)
    def server_response_new_chat(self, username, pfp, B):
        if B and username not in self.dh_key_for_each_user.keys():
            key = pow(int(B), self.pending_dh[username], self.generate_prime())
            shared_secret_bytes = key.to_bytes((key.bit_length() + 7) // 8, 'big')
            self.dh_key_for_each_user[username] = hashlib.sha256(shared_secret_bytes).digest()
        card = self.load_ui("ui/chatcard.ui")
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(pfp))
        card.findChild(QPushButton, "chat").setIcon(QIcon(self.get_perfect_circular_pixmap_from_pixmap(pixmap, 70)))
        card.findChild(QPushButton, "chat").setText(username)
        btn = card.findChild(QPushButton, "chat")
        btn.clicked.connect(lambda : self.on_chat(username, pixmap))
        self.chat_hub_list_layout.addWidget(card)
    @Slot(str, str, str)
    def add_invite(self, username, pfp, A):
        card = self.load_ui("ui/Card.ui")
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(pfp))
        card.findChild(QLabel, "pfp").setPixmap(self.get_perfect_circular_pixmap_from_pixmap(pixmap, 70))
        card.findChild(QLabel, "username").setText(username)
        card.findChild(QPushButton, "confirmbutton").clicked.connect(lambda: self.on_confirm(username, pfp, card, A))
        self.invite_list_layout.addWidget(card)
        self.bell_button.set_notifications(self.bell_button.notification_count + 1)



    @Slot(str)
    def server_response_no_more_users(self, data):
        QMessageBox.critical(self.main, "error", data)

    @Slot(str)
    def server_response_after_login(self, data):
        user_data = self.list_of_users[0].split("~")
        self.scroll_pfp.loadFromData(base64.b64decode(data))
        self.pfp_scroll.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.scroll_pfp))
        self.user_scroll.setText(f"UserName:{user_data[1]}")
        if user_data[3] == "1":
            self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobby, which is: {user_data[4]}")
        elif user_data[3] != "1" and user_data[3] != "0":
            self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobbies, which are: {user_data[4]}")
        else:
            self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobbies")
        self.stacked.setCurrentWidget(self.scroll)
    @Slot(list)
    def get_first_user_pfp(self, data):
        self.list_of_users = data
        user_data = data[0].split("~")
        if user_data[2] == "defaultpfp.png":
            print("Hello")
            self.user_scroll.setText(f"UserName:{user_data[1]}")
            if user_data[3] == "1":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobby, which is: {user_data[4]}")
            elif user_data[3] != "1" and user_data[3] != "0":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobbies, which are: {user_data[4]}")
            else:
                self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobbies")
            self.stacked.setCurrentWidget(self.scroll)
        else:
            send_with_AES(self.sock, f"GPOF|{user_data[2]}", self.DiffieHellmankey, self.IV)
    @Slot(bool, str)
    def server_response_login(self, type_msg, pfp):
        if type_msg:
            QMessageBox.information(self.main, "info", "Login Success!")
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(pfp))
            self.my_pfp = pixmap
            send_with_AES(self.sock, "GDFS|", self.DiffieHellmankey, self.IV)
        else:
            QMessageBox.critical(self.main, "error", "Login Failed!")

    @Slot(bool)
    def server_response_signup(self, msg_type):
        if not msg_type:
            QMessageBox.critical(self.main, "error", "Username already taken, pick a different one")
        else:
            self.stacked.setCurrentWidget(self.hobbies)

    @Slot(bool)
    def server_response_hobbies(self, msg_type):
        global icons_path
        if not msg_type:
            QMessageBox.critical(self.main, "error", "You took too long to answer, signup again")
            for box in self.checkbox:
                box.setChecked(False)
            self.password_signup.setText("")
            self.signup_username.setText("")
            self.signup_ip.setText("")
            if self.is_visible_signup:
                self.password_signup.setEchoMode(QLineEdit.Password)
                self.eyeSignup.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
                self.is_visible_signup = False
            self.stacked.setCurrentWidget(self.signup)
        else:
            self.pfp_signup.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))
            self.stacked.setCurrentWidget(self.upload_pfp_signup)

    @Slot(bool)
    def server_response_pfp(self, msg_type):
        self.password_signup.setText("")
        self.signup_username.setText("")
        self.signup_ip.setText("")
        if self.is_visible_signup:
            self.password_signup.setEchoMode(QLineEdit.Password)
            self.eyeSignup.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
            self.is_visible_signup = False
        for box in self.checkbox:
            box.setChecked(False)
        self.selected_image_path = ''
        self.is_pfp_default = True
        self.pfp_signup.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))
        self.stacked.setCurrentWidget(self.login)
        if not msg_type:
            QMessageBox.critical(self.main, "error", "You took too long to answer, signup again")
        else:
            QMessageBox.information(self.main,"info", "SignUp Success!")

    @Slot()
    def server_response_pfp_bug(self):
        QMessageBox.critical(self.main, "error", "There was an error while trying to upload your profile picture, please try again or pick a different one!")
        self.pfp_signup.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))

    @Slot()
    def server_response_login_steps(self, num):
        if num == 1:
            QMessageBox.critical(self.main, "error", "You didn't finish your signup process, you were in the middle of picking hobbies")
            for box in self.checkbox:
                box.setChecked(False)
            self.stacked.setCurrentWidget(self.hobbies)
        else:
            QMessageBox.critical(self.main, "error", "You didn't finish your signup process, you were in the middle of picking your profile picture")
            self.pfp_signup.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))
            self.stacked.setCurrentWidget(self.upload_pfp_signup)


    def on_scroll(self):
        if not self.list_of_users:
            user_data = self.last_user.split("~")
        else:
            user_data = self.list_of_users[0].split("~")
        if user_data[2] == "defaultpfp.png":
            self.pfp_scroll.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))
            self.user_scroll.setText(f"UserName:{user_data[1]}")
            if user_data[3] == "1":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobby, which is: {user_data[4]}")
            elif user_data[3] != "1" and user_data[3] != "0":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobbies, which are: {user_data[4]}")
            else:
                self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobbies")
        else:
            send_with_AES(self.sock, f"GPOF|{user_data[2]}", self.DiffieHellmankey, self.IV)
        self.stacked.setCurrentWidget(self.scroll)

    def on_confirm(self, username, pfp, card, A):
        p = self.generate_prime()
        g = 5
        a = secrets.randbelow(p - 2) + 1
        B = pow(g, a, p)
        key = pow(int(A), a, p)
        shared_secret_bytes = key.to_bytes((key.bit_length() + 7) // 8, 'big')
        self.dh_key_for_each_user[username] = hashlib.sha256(shared_secret_bytes).digest()
        send_with_AES(self.sock, f"INVA|{username}|{B}", self.DiffieHellmankey, self.IV)
        card.deleteLater()
        self.bell_button.set_notifications(self.bell_button.notification_count - 1)
        self.create_new_chat(username, pfp)
        self.stacked.setCurrentWidget(self.scroll)

    def create_new_chat(self, username, pfp):
        card = self.load_ui("ui/chatcard.ui")
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(pfp))
        card.findChild(QPushButton, "chat").setIcon(QIcon(self.get_perfect_circular_pixmap_from_pixmap(pixmap, 70)))
        card.findChild(QPushButton, "chat").setText(username)
        btn = card.findChild(QPushButton, "chat")
        btn.clicked.connect(lambda : self.on_chat(username, pixmap))
        self.chat_hub_list_layout.addWidget(card)

    def display_message(self, message, is_mine, timestamp):
        date_str = timestamp[:10]
        time_str = timestamp[11:16]
        if self.last_message_date != date_str:
            self.chat_layout.addWidget(DateSeparator(date_str))
            self.last_message_date = date_str
        self.chat_layout.addWidget(ChatBubble(message, is_mine, time_str))
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))


    def on_chat(self, username, pfp):
        self.current_chat_user = username
        self.current_user_pfp = pfp
        self.pfp_chat.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.current_user_pfp, 70))
        self.username_chat.setText(self.current_chat_user)

        # clear existing messages
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.last_message_date = None

        if username in self.message_buffer.keys() and self.message_buffer[username]:
            msgs = self.message_buffer[username]
            print(msgs)
            for i in msgs:
                self.display_message(i[0], i[1], i[2])
        self.user_in_chat = True
        self.stacked.setCurrentWidget(self.chat)




    def on_send(self):
        message = self.message_chat.text().strip()
        if not message:
            return
        key = self.dh_key_for_each_user[self.current_chat_user]
        iv = secrets.token_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(message.encode(), AES.block_size))
        send_with_AES(self.sock, f"MSFU|{self.current_chat_user}|{base64.b64encode(iv + encrypted).decode()}", self.DiffieHellmankey, self.IV)
        self.pending_sent_message[self.current_chat_user] = message
        self.message_chat.clear()

    def upload_pfp(self):
        pfp_path, _ = QFileDialog.getOpenFileName(self, "Select Profile Picture", "", "Image Files (*.png *.jpg *.jpeg)")

        if pfp_path:
            self.pfp_signup.setPixmap(self.get_perfect_circular_pixmap(pfp_path))
            self.selected_image_path = pfp_path
            self.is_pfp_default = False
        else:
            QMessageBox.critical(self.main, "error", "There was an error while trying to upload the picture, Please try again or select a different picture")

    def get_perfect_circular_pixmap_from_pixmap(self, pixmap, size=300):
        width = pixmap.width()
        height = pixmap.height()
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        square_pixmap = pixmap.copy(QRect(left, top, side, side))

        final_pixmap = QPixmap(size, size)
        final_pixmap.fill(Qt.transparent)

        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_square = square_pixmap.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.setBrush(QBrush(scaled_square))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()

        return final_pixmap

    def get_perfect_circular_pixmap(self, file_path, size=300):
        original_pixmap = QPixmap(file_path)
        if original_pixmap.isNull():
            return None

        width = original_pixmap.width()
        height = original_pixmap.height()
        side = min(width, height)

        left = (width - side) // 2
        top = (height - side) // 2
        square_rect = QRect(left, top, side, side)
        square_pixmap = original_pixmap.copy(square_rect)

        final_pixmap = QPixmap(size, size)
        final_pixmap.fill(Qt.transparent)

        painter = QPainter(final_pixmap)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        scaled_square = square_pixmap.scaled(size, size,
                                             Qt.IgnoreAspectRatio,
                                             Qt.SmoothTransformation)
        brush = QBrush(scaled_square)

        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        painter.drawEllipse(0, 0, size, size)
        painter.end()

        return final_pixmap

    def on_video(self):
        self.is_video = True
        if self.is_person_in_call[self.current_chat_user]:
            self.still_in_call = True
            self.person_in_call = self.current_chat_user
            self.person_in_call_pfp = self.current_user_pfp
            self.audio_running = True
            self.second_user_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.current_user_pfp, 70))
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button.setIcon(QIcon(file_path))
            send_with_AES(self.sock, f"CBUA|{self.person_in_call}", self.DiffieHellmankey, self.IV)
            Thread(target=self.capture_audio).start()
            Thread(target=self.playback_audio).start()
            Thread(target=self.capture_video).start()
            self.stacked.setCurrentWidget(self.call)
        else:
            self.still_in_call = True
            self.person_in_call = self.current_chat_user
            self.person_in_call_pfp = self.current_user_pfp
            self.audio_running = False
            self.text_alone.setText(f"Waiting for {self.person_in_call} to pickup")
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button_alone.setIcon(QIcon(file_path))
            Thread(target=self.capture_video).start()
            self.stacked.setCurrentWidget(self.audio_call_alone)
            send_with_AES(self.sock, f"SAAC|{self.person_in_call}", self.DiffieHellmankey, self.IV)
    def on_call(self):
        if self.is_person_in_call[self.current_chat_user]:
            self.still_in_call = True
            self.person_in_call = self.current_chat_user
            self.person_in_call_pfp = self.current_user_pfp
            self.audio_running = True
            self.second_user_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.current_user_pfp, 70))
            self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
            send_with_AES(self.sock, f"CBUA|{self.person_in_call}", self.DiffieHellmankey, self.IV)
            Thread(target=self.capture_audio).start()
            Thread(target=self.playback_audio).start()
            Thread(target=self.capture_video).start()
            self.stacked.setCurrentWidget(self.call)
        else:
            self.still_in_call = True
            self.person_in_call = self.current_chat_user
            self.person_in_call_pfp = self.current_user_pfp
            self.audio_running = False
            self.pfp_call_alone.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
            self.text_alone.setText(f"Waiting for {self.person_in_call} to pickup")
            self.stacked.setCurrentWidget(self.audio_call_alone)
            send_with_AES(self.sock, f"SAAC|{self.person_in_call}", self.DiffieHellmankey, self.IV)

    def capture_audio(self):
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        while self.audio_running:
            try:
                chunk = stream.read(1024, exception_on_overflow=False)
                if not self.is_mute and not self.is_deafen and not self.other_deafen:
                    iv = secrets.token_bytes(16)
                    cipher = AES.new(self.dh_key_for_each_user[self.person_in_call], AES.MODE_CBC, iv)
                    encrypted = cipher.encrypt(pad(chunk, AES.block_size))
                    encrypted_b64 = base64.b64encode(iv + encrypted).decode()
                    full_data = f"CATU|{self.person_in_call}|{encrypted_b64}"
                    cipher = AES.new(self.DiffieHellmankey, AES.MODE_CBC, self.IV.encode())
                    encrypted = cipher.encrypt(pad(full_data.encode(), AES.block_size))
                    self.udp_sock.sendto(encrypted, self.server_udp_addr)
            except Exception as e:
                print(f"Capture error: {e}")
                break
        stream.stop_stream()
        stream.close()

    def display_video_frame(self, sender, full_data):
        try:
            raw = base64.b64decode(full_data)
            iv, encrypted = raw[:16], raw[16:]
            cipher = AES.new(self.dh_key_for_each_user[sender], AES.MODE_CBC, iv)
            frame_bytes = unpad(cipher.decrypt(encrypted), AES.block_size)
            np_arr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            qt_image = QImage(frame.data.tobytes(), w, h, ch * w, QImage.Format_RGB888)
            self.second_user_pfp_call.setPixmap(QPixmap.fromImage(qt_image).scaled(self.second_user_pfp_call.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"Display error: {e}")


    def playback_audio(self):
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True, frames_per_buffer=1024)
        while self.audio_running:
            try:
                chunk = self.playback_queue.get(timeout=1)
                if not self.is_deafen and not self.other_deafen:
                    stream.write(chunk)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
                break
        stream.stop_stream()
        stream.close()

    def capture_video(self):
        if self.local_cap is not None:
            return
        self.local_cap = cv2.VideoCapture(0)
        while self.still_in_call and not self.is_video:
            self.local_cap.read()  # discard frames until camera is ready
            time.sleep(0.03)
        while self.still_in_call:
            if self.is_video:
                ret, frame = self.local_cap.read()
                if not ret:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qt_img = QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format_RGB888)
                self.my_video_signal.emit(QPixmap.fromImage(qt_img))
                if self.is_person_in_call.get(self.person_in_call, False):
                    frame_resized = cv2.resize(frame, (320, 240))
                    _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    raw = buffer.tobytes()
                    # E2EE: random IV between users
                    e2ee_iv = secrets.token_bytes(16)
                    cipher = AES.new(self.dh_key_for_each_user[self.person_in_call], AES.MODE_CBC, e2ee_iv)
                    encrypted = cipher.encrypt(pad(raw, AES.block_size))
                    encrypted_b64 = base64.b64encode(e2ee_iv + encrypted).decode()
                    self.udp_send_chunks(self.person_in_call, encrypted_b64)
            else:
                self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
                time.sleep(0.05)
        if self.local_cap is not None:
            self.local_cap.release()
            self.local_cap = None

    def udp_send_chunks(self, recipient, data):
        frame_id = secrets.token_hex(4)
        chunks = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            msg = f"VDFU|{recipient}|{frame_id}|{idx}|{total}|{chunk}"
            iv = self.IV.encode()
            cipher = AES.new(self.DiffieHellmankey, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(msg.encode(), AES.block_size))
            self.udp_sock.sendto(encrypted, self.server_udp_addr)

    def on_hangup_alone(self):
        global icons_path
        self.audio_running = False
        self.is_deafen = False
        self.is_mute = False
        self.still_in_call = False
        self.is_video = False
        self.current_chat_user = self.person_in_call
        self.current_user_pfp = self.person_in_call_pfp
        if self.is_video:
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button_alone.setIcon(QIcon(file_path))
            self.video_call_button.setIcon(QIcon(file_path))
        file_path = os.path.join(icons_path, "headphones.png")
        self.deafen_button_alone.setIcon(QIcon(file_path))
        self.deafen_button.setIcon(QIcon(file_path))
        file_path = os.path.join(icons_path, "mic.png")
        self.mic_button_alone.setIcon(QIcon(file_path))
        self.mic_button.setIcon(QIcon(file_path))
        self.current_chat_user = self.person_in_call
        self.pfp_chat.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.person_in_call_pfp, 70))
        self.username_chat.setText(self.current_chat_user)
        if self.current_chat_user in self.message_buffer.keys() and self.message_buffer[self.current_chat_user]:
            msgs = self.message_buffer[self.current_chat_user]
            print(msgs)
            for i in msgs:
                self.display_message(i[0], i[1], i[2])
        self.user_in_chat = True
        self.stacked.setCurrentWidget(self.chat)
        send_with_AES(self.sock, f"IHUT|{self.person_in_call}", self.DiffieHellmankey, self.IV)


    def on_hangup(self):
        global icons_path
        self.audio_running = False
        self.is_deafen = False
        self.is_mute = False
        self.still_in_call = False
        self.is_video = False
        if self.is_video:
            file_path = os.path.join(icons_path, "phone.png")
            self.video_call_button.setIcon(QIcon(file_path))
        self.current_chat_user = self.person_in_call
        self.current_user_pfp = self.person_in_call_pfp
        file_path = os.path.join(icons_path, "headphones.png")
        self.deafen_button.setIcon(QIcon(file_path))
        file_path = os.path.join(icons_path, "mic.png")
        self.mic_button.setIcon(QIcon(file_path))
        self.current_chat_user = self.person_in_call
        self.pfp_chat.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.person_in_call_pfp, 70))
        self.username_chat.setText(self.current_chat_user)
        if self.current_chat_user in self.message_buffer.keys() and self.message_buffer[self.current_chat_user]:
            msgs = self.message_buffer[self.current_chat_user]
            print(msgs)
            for i in msgs:
                self.display_message(i[0], i[1], i[2])
        self.user_in_chat = True
        self.stacked.setCurrentWidget(self.chat)
        send_with_AES(self.sock, f"IHTC|{self.person_in_call}", self.DiffieHellmankey, self.IV)


    def on_camera(self):
        global icons_path
        self.is_video = not self.is_video
        file_path = os.path.join(icons_path, "video.png" if self.is_video else "phone.png")
        self.video_call_button.setIcon(QIcon(file_path))
        if not self.is_video:
            self.my_pfp_call.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
            self.pfp_call_alone.setPixmap(self.get_perfect_circular_pixmap_from_pixmap(self.my_pfp, 70))
            send_with_AES(self.sock, f"ITOC|{self.person_in_call}", self.DiffieHellmankey, self.IV)


    def on_deafen(self):
        global icons_path
        self.is_deafen = not self.is_deafen
        file_path = os.path.join(icons_path, "deafen.png" if self.is_deafen else "headphones.png")
        self.deafen_button.setIcon(QIcon(file_path))
        if self.is_deafen:
            send_with_AES(self.sock, f"DION|{self.person_in_call}", self.DiffieHellmankey, self.IV)
        else:
            send_with_AES(self.sock, f"DOFF|{self.person_in_call}", self.DiffieHellmankey, self.IV)

    def on_mute(self):
        global icons_path
        self.is_mute = not self.is_mute
        file_path = os.path.join(icons_path, "mute.png" if self.is_mute else "mic.png")
        self.mic_button.setIcon(QIcon(file_path))

    def on_continue_pfp(self):
        if self.is_pfp_default:
            send_with_AES(self.sock, f"PFPS|DEFAULT", self.DiffieHellmankey, self.IV)
        else:
            with open(self.selected_image_path, "rb") as file:
                content = file.read()
            based_content = base64.b64encode(content).decode('utf-8')
            file_type = self.selected_image_path.split(".")[-1]
            send_with_AES(self.sock, f"PFPS|{file_type}|{based_content}", self.DiffieHellmankey, self.IV)

    def on_next(self):
        if not self.list_of_users:
            send_with_AES(self.sock, "GDFS|", self.DiffieHellmankey, self.IV)
            return
        else:
            user_data = self.list_of_users[0].split("~")
            self.last_user = self.list_of_users.pop(0)
        if user_data[2] == "defaultpfp.png":
            self.pfp_scroll.setPixmap(self.get_perfect_circular_pixmap(self.default_pfp_path))
            self.user_scroll.setText(f"UserName:{user_data[1]}")
            if user_data[3] == "1":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobby, which is: {user_data[4]}")
            elif user_data[3] != "1" and user_data[3] != "0":
                self.hobbies_scroll.setText(
                    f"You and {user_data[1]} share {user_data[3]} hobbies, which are: {user_data[4]}")
            else:
                self.hobbies_scroll.setText(f"You and {user_data[1]} share {user_data[3]} hobbies")
        else:
            send_with_AES(self.sock, f"GPOF|{user_data[2]}", self.DiffieHellmankey, self.IV)

    def on_invite(self):
        p = self.generate_prime()
        g = 5
        a = secrets.randbelow(p - 2) + 1
        A = pow(g, a, p)
        user_data = self.list_of_users[0].split("~")
        self.pending_dh[user_data[1]] = a
        send_with_AES(self.sock, f"INVI|{user_data[1]}|{A}", self.DiffieHellmankey, self.IV)
        self.on_next()

    def on_bell(self):
        self.stacked.setCurrentWidget(self.notifications)

    def Changing_to_signup(self):
        global icons_path
        self.stacked.setCurrentWidget(self.signup)
        self.password_login.setText("")
        self.login_username.setText("")
        self.login_ip.setText("")
        if self.is_visible_login:
            self.password_login.setEchoMode(QLineEdit.Password)
            self.eyeLogin.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
            self.is_visible_login = False


    def Changing_to_login(self):
        global icons_path
        self.stacked.setCurrentWidget(self.login)
        self.password_signup.setText("")
        self.signup_username.setText("")
        self.signup_ip.setText("")
        if self.is_visible_signup:
            self.password_signup.setEchoMode(QLineEdit.Password)
            self.eyeSignup.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
            self.is_visible_signup = False

    def ShowPasswordLogIn(self):
        global icons_path
        if not self.is_visible_login:
            self.password_login.setEchoMode(QLineEdit.Normal)
            self.eyeLogin.setIcon(QIcon(fr"{icons_path}\eyeopen.png"))
            self.is_visible_login = True
        else:
            self.password_login.setEchoMode(QLineEdit.Password)
            self.eyeLogin.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
            self.is_visible_login = False

    def ShowPasswordSignUp(self):
        global icons_path
        if not self.is_visible_signup:
            self.password_signup.setEchoMode(QLineEdit.Normal)
            self.eyeSignup.setIcon(QIcon(fr"{icons_path}\eyeopen.png"))
            self.is_visible_signup = True
        else:
            self.password_signup.setEchoMode(QLineEdit.Password)
            self.eyeSignup.setIcon(QIcon(fr"{icons_path}\eyeclosed.png"))
            self.is_visible_signup = False

    def OnLogin(self):
        username = self.login_username.text().strip()
        password = self.password_login.text().strip()
        ip = self.login_ip.text().strip()
        if username == "" or password == ""or ip == "":
            QMessageBox.critical(None, "error", "Please enter login credentials!")
            return
        if self.TheMainThread is not None and self.TheMainThread.isRunning():
            send_with_AES(self.sock, f"LOGQ|{username}|{password}", self.DiffieHellmankey, self.IV)
            return
        try:
            self.sock.fileno()
        except:
            self.sock = socket.socket()
            self.generated_dh = False
        try:
            self.sock.connect((ip, 5000))
        except socket.gaierror:
            QMessageBox.critical(None, "error","Wrong IP, Enter correct IP in order to login!")
            return
        except socket.error:
            pass
        if not self.generated_dh:
            self.DiffieHellman(self.sock)
            self.generated_dh = True
        self.TheMainThread = QThread()
        self.TheWorker = Worker(ip, 5000, self.DiffieHellmankey, self.IV, self.sock, self.udp_sock)

        self.TheWorker.moveToThread(self.TheMainThread)

        self.TheMainThread.started.connect(self.TheWorker.run)

        self.TheWorker.response_login.connect(self.server_response_login)
        self.TheWorker.response_signup.connect(self.server_response_signup)
        self.TheWorker.response_hobbies.connect(self.server_response_hobbies)
        self.TheWorker.response_pfp.connect(self.server_response_pfp)
        self.TheWorker.response_pfp_bug.connect(self.server_response_pfp_bug)
        self.TheWorker.response_login_steps.connect(self.server_response_login_steps)
        self.TheWorker.response_after_login.connect(self.get_first_user_pfp)
        self.TheWorker.response_after_user_pfp.connect(self.server_response_after_login)
        self.TheWorker.response_no_more_users.connect(self.server_response_no_more_users)
        self.TheWorker.request_for_chat.connect(self.add_invite)
        self.TheWorker.insert_new_chat.connect(self.server_response_new_chat)
        self.TheWorker.response_keys.connect(self.server_response_new_keys)
        self.TheWorker.new_message.connect(self.server_response_new_message)
        self.TheWorker.timestamp_for_message.connect(self.response_timestamp)
        self.TheWorker.set_keys.connect(self.response_set_keys)
        self.TheWorker.get_messages_from_offline.connect(self.response_msgs_offline)
        self.TheWorker.show_pop_up.connect(self.user_called_you)
        self.TheWorker.response_user_pickedup.connect(self.response_pickingup)
        self.TheWorker.got_audio.connect(self.response_got_audio)
        self.TheWorker.user_rejoined.connect(self.response_user_rejoined)
        self.TheWorker.user_hanged_up.connect(self.response_user_hanged_up)
        self.TheWorker.get_users_in_call.connect(self.response_do_in_call)
        self.TheWorker.enter_users_in_call.connect(self.response_dont_in_call)
        self.TheWorker.user_hanged_up_too.connect(self.response_user_hanged_up_too)
        self.TheWorker.other_deafened.connect(self.response_user_deafend)
        self.TheWorker.other_undeafened.connect(self.response_user_undeafend)
        self.TheWorker.video_stream.connect(self.response_got_video)
        self.TheWorker.finished.connect(self.TheMainThread.quit)
        self.TheWorker.finished.connect(self.TheWorker.deleteLater)
        self.TheMainThread.finished.connect(self.TheMainThread.deleteLater)

        send_with_AES(self.sock, f"LOGQ|{username}|{password}", self.DiffieHellmankey, self.IV)
        self.server_udp_addr = (ip, 5001)

        self.TheMainThread.start()

    def on_confirm_hobbies(self):
        selected_boxes = []
        for box in self.checkbox:
            if box.isChecked():
                selected_boxes.append(box.text())
        if len(selected_boxes) < 4:
            QMessageBox.warning(self.main, "Selection", "Please pick at least 4 hobbies!")
            return
        send_with_AES(self.sock, f"HOBB|{"~".join(selected_boxes)}", self.DiffieHellmankey, self.IV)

    def OnSignup(self):
        username = self.signup_username.text().strip()
        password = self.password_signup.text().strip()
        ip = self.signup_ip.text().strip()
        if username == "" or password == "" or ip == "":
            QMessageBox.critical(None, "error", "Please enter signup credentials!")
            return
        if self.TheMainThread is not None and self.TheMainThread.isRunning():
            send_with_AES(self.sock, f"REGQ|{username}|{password}", self.DiffieHellmankey, self.IV)
            return
        try:
            self.sock.fileno()
        except:
            self.sock = socket.socket()
            self.generated_dh = False
        try:
            self.sock.connect((ip, 5000))
        except socket.gaierror:
            QMessageBox.critical(None, "error","Wrong IP, Enter correct IP in order to login!")
            return
        except socket.error as e:
            QMessageBox.critical(None, "error",f"There was an error while trying to connect to the server, {e}")
            return
        if not self.generated_dh:
            self.DiffieHellman(self.sock)
            self.generated_dh = True
        self.TheMainThread = QThread()
        self.TheWorker = Worker(ip, 5000, self.DiffieHellmankey, self.IV, self.sock, self.udp_sock)

        self.TheWorker.moveToThread(self.TheMainThread)

        self.TheMainThread.started.connect(self.TheWorker.run)

        self.TheWorker.response_login.connect(self.server_response_login)
        self.TheWorker.response_signup.connect(self.server_response_signup)
        self.TheWorker.response_hobbies.connect(self.server_response_hobbies)
        self.TheWorker.response_pfp.connect(self.server_response_pfp)
        self.TheWorker.response_pfp_bug.connect(self.server_response_pfp_bug)
        self.TheWorker.response_login_steps.connect(self.server_response_login_steps)
        self.TheWorker.response_after_login.connect(self.get_first_user_pfp)
        self.TheWorker.response_after_user_pfp.connect(self.server_response_after_login)
        self.TheWorker.response_no_more_users.connect(self.server_response_no_more_users)
        self.TheWorker.request_for_chat.connect(self.add_invite)
        self.TheWorker.insert_new_chat.connect(self.server_response_new_chat)
        self.TheWorker.response_keys.connect(self.server_response_new_keys)
        self.TheWorker.new_message.connect(self.server_response_new_message)
        self.TheWorker.timestamp_for_message.connect(self.response_timestamp)
        self.TheWorker.set_keys.connect(self.response_set_keys)
        self.TheWorker.get_messages_from_offline.connect(self.response_msgs_offline)
        self.TheWorker.show_pop_up.connect(self.user_called_you)
        self.TheWorker.response_user_pickedup.connect(self.response_pickingup)
        self.TheWorker.got_audio.connect(self.response_got_audio)
        self.TheWorker.user_rejoined.connect(self.response_user_rejoined)
        self.TheWorker.user_hanged_up.connect(self.response_user_hanged_up)
        self.TheWorker.get_users_in_call.connect(self.response_do_in_call)
        self.TheWorker.enter_users_in_call.connect(self.response_dont_in_call)
        self.TheWorker.user_hanged_up_too.connect(self.response_user_hanged_up_too)
        self.TheWorker.other_deafened.connect(self.response_user_deafend)
        self.TheWorker.other_undeafened.connect(self.response_user_undeafend)
        self.TheWorker.video_stream.connect(self.response_got_video)
        self.TheWorker.finished.connect(self.TheMainThread.quit)
        self.TheWorker.finished.connect(self.TheWorker.deleteLater)
        self.TheMainThread.finished.connect(self.TheMainThread.deleteLater)

        send_with_AES(self.sock,f"REGQ|{username}|{password}", self.DiffieHellmankey, self.IV)
        self.server_udp_addr = (ip, 5001)

        self.TheMainThread.start()


    def closeEvent(self, event):
        print("Closing application...")
        if self.password and self.username:
            salt = secrets.token_bytes(16)
            storage_key = hashlib.pbkdf2_hmac('sha256', self.password.encode(), salt, 100000)

            data = {
                "dh_keys": {k: v.hex() for k, v in self.dh_key_for_each_user.items()},
                "pending_dh": {k: str(v) for k, v in self.pending_dh.items()}
            }
            json_bytes = json.dumps(data).encode()
            iv = secrets.token_bytes(16)
            cipher = AES.new(storage_key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(json_bytes, AES.block_size))

            with open(f"{self.username}_keys.enc", "wb") as f:
                f.write(salt + iv + encrypted)
        if self.TheMainThread is not None and self.TheMainThread.isRunning():
            try:
                if self.sock and self.DiffieHellmankey:
                    if self.still_in_call:
                        if self.is_person_in_call[self.person_in_call]:
                            send_with_AES(self.sock, f"IHTC|{self.person_in_call}", self.DiffieHellmankey, self.IV)
                        else:
                            send_with_AES(self.sock, f"IHUT|{self.person_in_call}", self.DiffieHellmankey, self.IV)
                    send_with_AES(self.sock, "EXIT|", self.DiffieHellmankey, self.IV)
                    print("Exit message sent to server.")
            except KeyError:
                send_with_AES(self.sock, f"IHUT|{self.person_in_call}", self.DiffieHellmankey, self.IV)
            except Exception as e:
                print(f"Could not send exit message: {e}")
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception as e:
                print(f"Socket cleanup error: {e}")
            self.TheMainThread.quit()
            if not self.TheMainThread.wait(2000):
                print("Thread didn't stop, forcing termination.")
                self.TheMainThread.terminate()

        event.accept()

    def load_ui(self, path):
        f = QFile(path)
        if not f.exists():
            raise FileNotFoundError(f"UI file not found: {path}")

        if not f.open(QFile.ReadOnly):
            raise RuntimeError(f"Couldn't open UI file: {path}")

        loader = QUiLoader()
        loader.registerCustomWidget(BellButton)
        w = loader.load(f)
        f.close()

        if w is None:
            raise RuntimeError(f"QUiLoader failed to load UI: {path}")

        return w

    def generate_prime(self):
        p_hex = """
            FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
            29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
            EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
            E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
            EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE65381
            FFFFFFFF FFFFFFFF
        """.replace('\n', '').replace(' ', '')
        return int(p_hex, 16)

    def DiffieHellman(self, s: socket.socket):
        data = recv_by_size(s).decode('utf-8')
        splited_data = data.split('|')
        p = int(splited_data[1])
        g = int(splited_data[2])
        a = secrets.randbelow(p - 2) + 1
        A = pow(g, a, p)
        send_with_size(s, f'DIFHEL|{str(A)}')
        data = recv_by_size(s).decode('utf-8')
        splited_data = data.split('|')
        B = int(splited_data[1])
        key = pow(B, a, p)
        shared_secret_bytes = key.to_bytes((key.bit_length() + 7) // 8, 'big')

        self.generated_dh = True
        self.DiffieHellmankey = hashlib.sha256(shared_secret_bytes).digest()
