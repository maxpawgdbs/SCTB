from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import telebot  # Telegram Bot
import threading  # Многопоточность
import datetime  # Дата и время
import sqlite3  # БД
import os


class SystemControlTelegramBot(QMainWindow):  # Главное окно с чатом
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None  # Состояние окна с БД; None - окно закрыто
        self.con_com = None  # Состояние окна с конструктором команд; None - окно закрыто
        self.window()

    def window(self):
        global token
        self.setWindowTitle("Система Управления Telegram Бота")
        self.move(300, 300)
        self.setFixedSize(880, 560)

        self.message_history = QListWidget(self)  # История сообщений
        self.message_history.resize(500, 500)
        self.message_history.move(10, 10)

        self.message_edit = QLineEdit(self)  # Поле для ввода сообщения
        self.message_edit.resize(300, 30)
        self.message_edit.move(10, 520)

        self.user_choose = QComboBox(self)  # Выбор пользователя который получит сообщение при отправке
        self.user_choose.resize(350, 30)
        self.user_choose.move(520, 10)
        self.user_choose.addItem("Все")

        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()

        self.users = cur.execute("""SELECT * FROM users""").fetchall()  # Вся информация о пользователях
        self.users_id = [x[0] for x in self.users]  # user-id каждого пользователя

        self.chats = cur.execute("""SELECT * FROM chats""").fetchall()  # Вся информация о чатах
        self.chats_id = [int(x[0]) for x in self.chats]  # chat-id каждого чата

        for userid in self.users:  # Добавление пользователей и чатов в self.user_choose
            self.user_choose.addItem(" ; ".join([str(x) for x in userid]))
        for chat in self.chats:
            self.user_choose.addItem(" ; ".join([str(x) for x in chat]))

        self.commands_list = cur.execute("""SELECT * FROM commands
                                    WHERE token = '{}' """.format(token)).fetchall()  # Список команд

        con.close()

        self.commands_dict = dict()  # Словарь с командами
        for i in range(len(self.commands_list)):
            self.commands_dict[self.commands_list[i][1]] = self.commands_list[i][2]

        self.send_button = QPushButton("Отправить", self)  # Кнопка для отправки сообщения из self.message_edit
        self.send_button.resize(90, 30)
        self.send_button.move(320, 520)
        self.send_button.clicked.connect(self.send_message)

        self.send_file_button = QPushButton("Отпр. файл", self)  # Кнопка для отправки файла
        self.send_file_button.resize(90, 30)
        self.send_file_button.move(420, 520)
        self.send_file_button.clicked.connect(self.send_file)

        self.open_db_button = QPushButton("Открыть БД", self)  # Кнопка для открытия БД
        self.open_db_button.resize(350, 30)
        self.open_db_button.move(520, 50)
        self.open_db_button.clicked.connect(self.open_database_fnc)

        self.open_cc_button = QPushButton("Конструктор команд", self)  # Кнопка для открытия конструктора команд
        self.open_cc_button.resize(350, 30)
        self.open_cc_button.move(520, 90)
        self.open_cc_button.clicked.connect(self.open_cc_fnc)

    def auto_answer(self, message):  # Автоматический ответ, если сообщение является командой
        if message.text in self.commands_dict:
            con = sqlite3.connect("db-sctb.sqlite")
            cur = con.cursor()
            bot.send_message(message.chat.id, self.commands_dict[message.text])  # Отправка сообщения
            self.message_history.addItem(
                QListWidgetItem(
                    "<bot to chat-id: {}; user-id: {}; username: {};\nname: {}; lastname: {};\ntime: {}> {}\n".format(
                        message.chat.id, message.from_user.id, message.from_user.username, message.from_user.first_name,
                        message.from_user.last_name,
                        datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                        self.commands_dict[message.text])))  # Добавление сообщения в self.message_history
            cur.execute(  # Сохранение ответа в БД
                """INSERT INTO
                messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                VALUES('{}', {}, {}, '{}', ?, ?, '{}', 'text', ?) """.format(
                    token,
                    message.from_user.id,
                    message.chat.id,
                    "bot to @" + str(message.from_user.username),
                    datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                ("bot to " + str(message.from_user.first_name),
                 "bot to " + str(message.from_user.last_name), self.commands_dict[message.text]))

            con.commit()
            con.close()

    def open_cc_fnc(self):  # Открытие конструктора команд, если он закрыт
        if self.con_com is None:
            self.con_com = CommandConstructor()
        self.con_com.show()

    def new_id(self, message):  # Проверка наличия user-id и chat-id в БД
        if message.from_user.id not in self.users_id:  # Если user-id нет в self.users_id
            con = sqlite3.connect("db-sctb.sqlite")
            cur = con.cursor()

            self.users_id.append(message.from_user.id)  # Добавление user-id в self.users_id
            self.users.append((message.from_user.id, str(message.from_user.username),
                               message.from_user.first_name,
                               str(message.from_user.last_name)))  # Добавление пользователя в self.users
            self.user_choose.addItem("{} ; {} ; {} ; {}".format(message.from_user.id, message.from_user.username,
                                                          message.from_user.first_name,
                                                          message.from_user.last_name))
            # Добавление пользователя в self.user_choose
            cur.execute("""INSERT INTO users(user_id, user_name, name, lastname) VALUES({}, '{}', ?, ?)""".format(
                message.from_user.id, message.from_user.username),
                (message.from_user.first_name, str(message.from_user.last_name)))  # Сохранение пользователя в БД
            con.commit()
            con.close()

        elif message.from_user.id in self.users_id and \
                (message.from_user.id, str(message.from_user.username),
                 message.from_user.first_name,
                 str(message.from_user.last_name)) not in self.users:  # Если пользователь сменил имя или username
            con = sqlite3.connect("db-sctb.sqlite")
            cur = con.cursor()

            for i in range(len(self.users)):
                if self.users[i][0] == message.from_user.id:  # Ищем пользователя и удаляем его из списка
                    self.users.pop(i)
                    break
            self.users.append((message.from_user.id, str(message.from_user.username),
                               message.from_user.first_name,
                               str(message.from_user.last_name)))  # Добавляем обновленную информацию о пользователе

            self.user_choose.clear()  # Перезаписываем self.user_choose
            self.user_choose.addItem("Все")
            for userid in self.users:
                self.user_choose.addItem(" ; ".join([str(x) for x in userid]))
            for chat in self.chats:
                self.user_choose.addItem(" ; ".join([str(x) for x in chat]))

            cur.execute("""DELETE FROM users WHERE user_id = {}""".format(message.from_user.id))
            cur.execute("""INSERT INTO users(user_id, user_name, name, lastname) VALUES({}, '{}', ?, ?)""".format(
                message.from_user.id, message.from_user.username),
                (message.from_user.first_name, str(message.from_user.last_name)))  # Обновление информации в БД
            con.commit()
            con.close()

        if message.chat.id != message.from_user.id:  # Если user-id не равно chat-id

            if message.chat.id not in self.chats_id:  # Если chat-id нет в self.chats-id
                con = sqlite3.connect("db-sctb.sqlite")
                cur = con.cursor()

                self.chats_id.append(message.chat.id)  # Добавление chat-id в self.chats_id
                self.chats.append((message.chat.id, message.chat.title))  # Добавление чата в self.chats
                self.user_choose.addItem("{} ; {}".format(message.chat.id, message.chat.title))
                # Добавление чата в self.user_choose
                cur.execute("""INSERT INTO chats(chat_id, title) VALUES({}, ?)""".format(message.chat.id),
                            (message.chat.title,))  # Сохранение чата в БД
                con.commit()
                con.close()

            elif message.chat.id in self.chats_id and (message.chat.id, message.chat.title) not in self.chats:
                # Если в чате сменили название
                con = sqlite3.connect("db-sctb.sqlite")
                cur = con.cursor()

                for i in range(len(self.chats)):  # Поиск и удаление чата из self.chats
                    if self.chats[i][0] == message.chat.id:
                        self.chat.pop(i)
                        break
                self.chats.append((message.chat.id, message.chat.title))  # Добавление обновленной информации о чате

                self.user_choose.clear()  # Перезапись self.user_choose
                self.user_choose.addItem("Все")
                for userid in self.users:
                    self.user_choose.addItem(" ; ".join([str(x) for x in userid]))
                for chat in self.chats:
                    self.user_choose.addItem(" ; ".join([str(x) for x in chat]))

                cur.execute("""DELETE FROM chats WHERE chat_id = {}""".format(message.chat.id))
                cur.execute("""INSERT INTO users(chat_id, title) VALUES({}, ?)""".format(message.chat.id),
                            (message.chat.title,))  # Обновление информации в БД
                con.commit()
                con.close()

    def add_text_message(self, message):  # Добавление полученного сообщения в self.message_history и в БД
        global token  # В БД вместе с сообщением сохраняется токен активного бота
        word = "<chat-id: {}; user-id: {};\nusername: @{}; name: {}; lastname: {};\ntype: text; time: {};> {}\n".format(
            message.chat.id, message.from_user.id, message.from_user.username, message.from_user.first_name,
            message.from_user.last_name, datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3],
            message.text)  # Текст для self.message_hictory
        self.message_history.addItem(QListWidgetItem(word))  # Добавление текста в self.message_history

        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()
        cur.execute(
            """INSERT INTO messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
            VALUES('{}', {}, {}, '{}', ?, ?, '{}', '{}', ?) """.format(
                token,
                message.chat.id,
                message.from_user.id,
                message.from_user.username,
                datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3],
                message.content_type),
            (message.from_user.first_name, str(message.from_user.last_name), message.text))  # Сохранение сообщения в БД
        con.commit()
        con.close()

    def send_message(self):  # Отправка сообщения из self.message_edit выбранному в self.user_choose пользователю
        global token  # В БД вместе с сообщением сохраняется токен активного бота
        try:  # На случай, если нельяз отправить сообщение пользователю или в чат
            if len(self.message_edit.text()) != 0:  # Если self.message_edit не пуст
                con = sqlite3.connect("db-sctb.sqlite")
                cur = con.cursor()

                userid = self.user_choose.currentText().split(" ; ")  # Расскладываем текст из self.user_choose
                if self.user_choose.currentText() != "Все":  # Если выбран пользователь или чат
                    bot.send_message(int(userid[0]), self.message_edit.text())  # Отправка сообщения
                    if len(userid) == 4:  # Если выбран пользователь
                        self.message_history.addItem(
                            QListWidgetItem(
                                "<bot to user_id: {}; username: {};\nname: {}; lastname: {};\ntime: {}> {}\n".format(
                                    userid[0], userid[1], userid[2], userid[3],
                                    datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                    self.message_edit.text())))  # Добавление сообщения в self.message_history
                        cur.execute(
                            """INSERT INTO
                            messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                            VALUES('{}', {}, {}, '{}', ?, ?, '{}', 'text', ?) """.format(
                                token,
                                userid[0],
                                userid[0],
                                "bot to @" + userid[1],
                                datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                            ("bot to " + userid[2], "bot to " + userid[3],
                             self.message_edit.text()))  # Добавление сообщения в БД
                    if len(userid) == 2:  # Если выбран чат
                        self.message_history.addItem(
                            QListWidgetItem(
                                "<bot to chat_id: {}; title: {};\ntime: {}> {}\n".format(userid[0], userid[1],
                                                                                         datetime.datetime.now()
                                                                                         .strftime("%H:%M:%S.%f")[:-3],
                                                                                         self.message_edit.text())))
                        # Добавление сообщения в self.message_history
                        cur.execute(
                            """INSERT INTO
                            messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                            VALUES('{}', {}, {}, '{}', ?, ?, '{}', 'text', ?) """.format(
                                token,
                                userid[0],
                                userid[0],
                                "bot to " + userid[1],
                                datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                            ("bot to " + userid[1], "bot to " + userid[1], self.message_edit.text()))
                        # Добавление сообщения в БД

                else:  # Если в self.user_choose выбрано "Все"
                    if len(self.users_id) != 0 or len(self.chats_id) != 0:  # Если БД не пуста
                        for line in self.users_id:  # Отправка сообщений пользователям
                            try:  # Если пользователь заблокировал бота или писал только в чате
                                bot.send_message(int(line), self.message_edit.text())
                            except Exception:
                                pass
                        for line in self.chats_id:  # Отправка сообщений в чаты
                            try:  # Если бота удалили из чата
                                bot.send_message(int(line), self.message_edit.text())
                            except Exception:
                                pass
                        self.message_history.addItem(QListWidgetItem("<bot to all {}> {}\n".format(
                            datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                            self.message_edit.text())))  # Добавление сообщения в self.message_history
                        cur.execute(
                            """INSERT INTO
                            messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                            VALUES('{}', 12345, 12345, 'bot to all', 'bot to all', 'bot to all', '{}', 'text', ?) """.
                            format
                            (token,
                             datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                            (self.message_edit.text(),))  # Добавление сообщения в БД

                con.commit()
                con.close()
        except Exception:
            con.close()  # Закрытие БД, если выбранный пользователь/чат не доступен

    def add_file_message(self, message):  # Получение файлов
        if message.content_type == "photo":  # Если файл является фотографией
            file = bot.get_file(file_id := message.photo[-1].file_id)  # Получение файла и file-id

        elif message.content_type == "sticker":  # Если файл является стикером
            file = bot.get_file(file_id := message.sticker.file_id)  # Получение файла и file-id

        elif message.content_type in ["video", "video_note", "animation"]:  # Если файл является видео, кружком или gif
            if message.content_type == "video":
                file = bot.get_file(file_id := message.video.file_id)  # Получение файла и file-id
            elif message.content_type == "video_note":
                file = bot.get_file(file_id := message.video_note.file_id)  # Получение файла и file-id
            elif message.content_type == "animation":
                file = bot.get_file(file_id := message.animation.file_id)  # Получение файла и file-id

        elif message.content_type in ["voice", "audio"]:  # Получение аудио файла
            if message.content_type == "audio":
                file = bot.get_file(file_id := message.audio.file_id)  # Получение файла и file-id
            elif message.content_type == "voice":
                file = bot.get_file(file_id := message.voice.file_id)  # Получение файла и file-id

        elif message.content_type == "document":  # Получение файла без категории
            file = bot.get_file(file_id := message.document.file_id)  # Получение файла и file-id

        format_type = file.file_path[file.file_path.rfind("."):]  # Получение формата файла
        filename = "tgbotfiles/file-" + file_id + format_type  # Название файла
        downloaded_file = bot.download_file(file.file_path)  # Получение содержимого файла

        with open(filename, 'wb') as new_file:
            new_file.write(downloaded_file)  # Сохранение файла

        global token  # В БД вместе с сообщением сохраняется токен активного бота

        word = "<chat-id: {}; user-id: {};\nusername: @{}; name: {}; lastname: {};\ntype: {}; time: {};> path: {}\n". \
            format(message.chat.id, message.from_user.id, message.from_user.username, message.from_user.first_name,
                   message.from_user.last_name, message.content_type,
                   datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3],
                   filename)  # Текст для self.message_hictory
        self.message_history.addItem(QListWidgetItem(word))  # Добавление текста в self.message_history

        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()
        cur.execute(
            """INSERT INTO messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
            VALUES('{}', {}, {}, '{}', ?, ?, '{}', '{}', ?) """.format(
                token,
                message.chat.id,
                message.from_user.id,
                message.from_user.username,
                datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3],
                message.content_type),
            (message.from_user.first_name, str(message.from_user.last_name), filename))  # Сохранение сообщения в БД
        con.commit()
        con.close()

    def send_file(self):  # Отправка файла выбранному в self.user_choose пользователю/чата
        global token  # В БД вместе с сообщением сохраняется токен активного бота
        try:  # На случай, если нельяз отправить сообщение пользователю или в чат
            con = sqlite3.connect("db-sctb.sqlite")
            cur = con.cursor()

            filename = QFileDialog.getOpenFileName(self, 'Выбрать файл', '')[0]  # Выбор файла и получение его пути
            userid = self.user_choose.currentText().split(" ; ")  # Расскладываем текст из self.user_choose
            if self.user_choose.currentText() != "Все":  # Если выбран пользователь/чат
                bot.send_document(int(userid[0]), document=open(filename, 'rb'))  # Отправка файла
                if len(userid) == 4:  # Если выбран пользователь
                    self.message_history.addItem(
                        QListWidgetItem(
                            "<bot to user-id: {}; username: @{};\nname: {}; lastname: {}; time: {}> file: {}\n".format(
                                userid[0], userid[1], userid[2], userid[3],
                                datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                filename)))  # Добавление информации об отправке в self.message_history

                    cur.execute(
                        """INSERT INTO
                        messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                        VALUES('{}', {}, {}, '{}', ?, ?, '{}', 'file', ?) """.format(
                            token,
                            userid[0],
                            userid[0],
                            "bot to @" + userid[1],
                            datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                        ("bot to " + userid[2], "bot to " + userid[3], filename))  # Сохранение информации в БД

                elif len(userid) == 2:
                    self.message_history.addItem(
                        QListWidgetItem(
                            "<bot to chat-id: {}; title: {};\ntime: {}> file: {}\n".format(
                                userid[0], userid[1],
                                datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                                filename)))  # Добавление информации об отправке в self.message_history

                    cur.execute(
                        """INSERT INTO
                        messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                        VALUES('{}', {}, {}, '{}', ?, ?, '{}', 'file', ?) """.format(
                            token,
                            userid[0],
                            userid[0],
                            "bot to " + userid[1],
                            datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                        ("bot to " + userid[1], "bot to " + userid[1], filename))  # Сохранение информации в БД

            else:  # Если в self.user_choose выбрано "Все"
                if len(self.users_id) != 0 or len(self.chats_id) != 0:  # Если БД не пуста
                    for line in self.users_id:  # Отправка файла пользователям
                        try:  # Если пользователь заблокировал бота или писал только в чате
                            bot.send_document(int(line), document=open(filename, 'rb'))
                        except Exception:
                            pass
                    for line in self.chats_id:  # Отправка файла в чаты
                        try:  # Если бота удалили из чата
                            bot.send_document(int(line), document=open(filename, 'rb'))
                        except Exception:
                            pass
                    self.message_history.addItem(QListWidgetItem("<bot to all; time: {}> file: {}\n".format(
                        datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                        filename)))  # Добавление в self.message_history информации о сообщении

                    cur.execute(
                        """INSERT INTO
                        messagehistory(token, user_id, chat_id, user_name, name, lastname, time, type, message_path)
                        VALUES('{}', 12345, 12345, 'bot to all', 'bot to all', 'bot to all', '{}', 'file', ?) """.
                        format
                        (token,
                         datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S.%f")[:-3]),
                        (filename,))  # Сохранение информации в БД

            con.commit()
            con.close()
        except Exception:  # Закрытие БД, если пользователю не отправляется сообщение
            con.close()

    def keyPressEvent(self, event):  # Активация функции отправки файла при нажатии на "Enter"
        if event.key() == Qt.Key_Return:
            self.send_message()

    def closeEvent(self, event):  # Действия при закрытии окна
        global bot
        bot.stop_polling()  # Остановка бота
        if self.db is not None:  # Закрытие окна с БД, если оно открыто
            self.db.close()
        if self.con_com is not None:  # Закрытие окна с конструктором команд, если оно открыто
            self.con_com.close()
        event.accept()

    def open_database_fnc(self):  # Открытие БД
        if self.db is None:  # Если окно с БД закрыто
            self.db = DataBase()
        self.db.show()


class ChooseApiToken(QMainWindow):  # Окно выбора токена
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window()

    def window(self):
        self.setWindowTitle("Выбор API-Tokena")
        self.move(300, 300)
        self.setFixedSize(430, 150)

        self.token_choose = QComboBox(self)  # Поле выбора токена
        self.token_choose.resize(300, 50)
        self.token_choose.move(10, 10)

        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()
        token_names = cur.execute("""SELECT * FROM apitokens""").fetchall()  # Получение токенов из БД

        if len(token_names) != 0:  # Если БД не пуста
            for i in token_names:
                self.token_choose.addItem("<{}> {}".format(i[1], i[0]))  # Добавляем токены в self.token_choose
        else:  # Если БД пуста
            token, ok_pressed = QInputDialog.getText(self, "Введите  API Token", "Введите  API Token")  # Получаем токен
            if not ok_pressed:
                sys.exit()

            name, ok_pressed = QInputDialog.getText(self, "Введите название бота",
                                                    "Введите название бота")  # Получаем имя для бота
            if not ok_pressed:
                sys.exit()

            cur.execute("""INSERT INTO apitokens(token, name) VALUES('{}', '{}')""".format(token, name))
            con.commit()  # Сохраняем в БД

            self.token_choose.addItem("<{}> {}".format(name, token))  # Добавляем токен в self.token_choose

        con.close()

        self.add_token = QPushButton("Добавить бота", self)  # Кнопка для активации фунции получения токена
        self.add_token.resize(410, 30)
        self.add_token.move(10, 70)
        self.add_token.clicked.connect(self.add_token_func)

        self.del_token = QPushButton("Удалить бота", self)  # Кнопка для активации фунции удаления токена
        self.del_token.resize(410, 30)
        self.del_token.move(10, 110)
        self.del_token.clicked.connect(self.del_token_func)

        self.choose_button = QPushButton("Запуск", self)  # Запуск бота
        self.choose_button.resize(100, 50)
        self.choose_button.move(320, 10)
        self.choose_button.clicked.connect(self.token_choosed)

    def token_choosed(self):  # Запуск бота
        global token, choosed
        token = self.token_choose.currentText().split()[-1]
        choosed = True
        self.close()

    def add_token_func(self):  # Добавление токена
        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()
        token, ok_pressed = QInputDialog.getText(self, "Введите API Token", "Введите API Token")

        if ok_pressed:
            token_is = cur.execute("""SELECT * FROM apitokens
                                        WHERE token = '{}' """.format(token)).fetchall()
            if len(token_is) != 0:
                while True:
                    new_token, ok_pressed = QInputDialog.getText(self,
                                                                 "Введите НОВЫЙ API Token",
                                                                 "Введите НОВЫЙ API Token")
                    if new_token != token:
                        break
                    if not ok_pressed:
                        break
            if ok_pressed:
                name, ok_pressed = QInputDialog.getText(self, "Введите название бота", "Введите название бота")
                if ok_pressed:
                    cur.execute("""INSERT INTO apitokens(token, name) VALUES('{}', '{}')""".format(token, name))
                    con.commit()
                    self.token_choose.addItem("<{}> {}".format(name, token))
        con.close()

    def keyPressEvent(self, event):  # Запуск бота при нажатии "Enter"
        if event.key() == Qt.Key_Return:
            self.token_choosed()

    def del_token_func(self):  # Удаление токена
        token_name = self.token_choose.currentText()
        self.token_choose.clear()
        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()
        cur.execute("""DELETE FROM apitokens
                    WHERE token = '{}' """.format(token_name.split()[-1]))
        con.commit()
        token_names = cur.execute("""SELECT * FROM apitokens""").fetchall()
        con.close()
        if len(token_names) != 0:
            for i in token_names:
                self.token_choose.addItem("<{}> {}".format(i[1], i[0]))
        else:
            token, ok_pressed = QInputDialog.getText(self, "Введите  API Token", "Введите  API Token")
            if not ok_pressed:
                self.close()
            else:
                name, ok_pressed = QInputDialog.getText(self, "Введите название бота", "Введите название бота")
                if not ok_pressed:
                    sys.close()

            if ok_pressed:
                cur.execute("""INSERT INTO apitokens(token, name) VALUES('{}', '{}')""".format(token, name))
                con.commit()
                self.token_choose.addItem("<{}> {}".format(name, token))


class DataBase(QWidget):  # Окно БД
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window()

    def window(self):
        global token
        self.setWindowTitle("База данных")
        self.move(300, 300)
        self.setFixedSize(1580, 700)

        self.table = QTableWidget(self)  # Таблица сообщений
        self.table.resize(1200, 680)
        self.table.move(10, 10)

        self.table.setColumnCount(8)

        con = sqlite3.connect("db-sctb.sqlite")
        cur = con.cursor()

        self.messages = cur.execute("""SELECT * FROM messagehistory
                                    WHERE token = '{}' """.format(
            token)).fetchall()  # Получение сообщений выбранного бота

        self.fill_table(self.messages)  # Вызов функции для заполнения таблицы

        self.choose_chat = QComboBox(self)  # Выбор чата
        self.choose_chat.resize(350, 30)
        self.choose_chat.move(1220, 10)

        self.choose_user = QComboBox(self)  # Выбор пользователя
        self.choose_user.resize(350, 30)
        self.choose_user.move(1220, 50)

        self.chats = cur.execute("""SELECT * FROM chats""").fetchall()  # Получение информации о чатах
        self.choose_chat.addItem("Все")
        self.choose_chat.addItems([" ; ".join([str(x) for x in chat]) for chat in self.chats])
        # Добавление чатов в self.choose_chat

        self.users = cur.execute("""SELECT * FROM users""").fetchall()  # Получение информации о пользователях
        self.choose_user.addItem("Все")
        self.choose_user.addItems([" ; ".join([str(x) for x in user]) for user in self.users])
        # Добавление пользоватлей в self.choose_user

        self.find = QPushButton("Поиск", self)  # Кнопка для активации функции поиска по выбранным данным
        self.find.resize(350, 30)
        self.find.move(1220, 90)
        self.find.clicked.connect(self.find_fnc)

        con.close()

    def fill_table(self, spisok):  # Заполнение таблицы
        self.table.clear()  # Очищаем таблицу и создаем колонки
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem("chat-id"))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem("user-id"))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem("username"))
        self.table.setHorizontalHeaderItem(3, QTableWidgetItem("name"))
        self.table.setHorizontalHeaderItem(4, QTableWidgetItem("lastname"))
        self.table.setHorizontalHeaderItem(5, QTableWidgetItem("type"))
        self.table.setHorizontalHeaderItem(6, QTableWidgetItem("time"))
        self.table.setHorizontalHeaderItem(7, QTableWidgetItem("message/path"))
        self.table.horizontalHeaderItem(7).setTextAlignment(Qt.AlignLeft)

        if len(spisok) != 0:  # Если БД не пуста
            self.table.setRowCount(len(spisok))  # Задаем количество строк
            for y in range(len(spisok)):
                for x in range(8):  # Заполняем таблицу
                    item = QTableWidgetItem(str(spisok[y][x + 1]))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(y, x, item)

            self.table.resizeColumnsToContents()

    def find_fnc(self):  # Поиск по выбранным данным
        if self.choose_chat.currentText() == "Все" and self.choose_user.currentText() == "Все":
            # Если выбрано "Все", то просто вызываем функцию
            self.fill_table(self.messages)

        elif self.choose_chat.currentText() == "Все" and self.choose_user.currentText() != "Все":
            # Если чаты все, а пользователи нет
            need_messages = list()
            userid = self.choose_user.currentText().split(" ; ")[0]
            for message in self.messages:  # Фильтруем сообщения
                if str(message[2]) == userid:
                    need_messages.append(message)

            self.fill_table(need_messages)  # Заполняем таблицу

        elif self.choose_chat.currentText() != "Все" and self.choose_user.currentText() == "Все":
            # Если чат выбран, а пользователь нет
            need_messages = list()
            chatid = self.choose_chat.currentText().split(" ; ")[0]
            for message in self.messages:  # Фильтруем сообщения
                if str(message[1]) == chatid:
                    need_messages.append(message)

            self.fill_table(need_messages)  # Заполняем таблицу

        elif self.choose_chat.currentText() != "Все" and self.choose_user.currentText() != "Все":
            # Выбран и чат, и пользователь
            need_messages = list()
            chatid = self.choose_chat.currentText().split(" ; ")[0]
            userid = self.choose_user.currentText().split(" ; ")[0]
            for message in self.messages:  # Фильтруем сообщения
                if str(message[1]) == chatid and str(message[2]) == userid:
                    need_messages.append(message)

            self.fill_table(need_messages)  # Заполняем таблицу


class CommandConstructor(QWidget):  # Окно конструктора команд
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window()

    def window(self):
        global window
        self.setWindowTitle("Конструтор команд")
        self.setFixedSize(530, 500)
        self.move(300, 300)

        self.table_commands = QTableWidget(self)  # Таблица с командами
        self.table_commands.resize(300, 480)
        self.table_commands.move(10, 10)

        self.table_commands.setColumnCount(2)  # Создание колонок
        self.table_commands.setHorizontalHeaderItem(0, QTableWidgetItem("message"))
        self.table_commands.setHorizontalHeaderItem(1, QTableWidgetItem("answer"))
        self.table_commands.setRowCount(len(window.commands_dict))

        for y in range(len(window.commands_list)):
            for x in range(2):
                item = QTableWidgetItem(window.commands_list[y][x + 1])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table_commands.setItem(y, x, item)
        # Заполнение таблицы данными, хранящимися в основном окне в переменной window.commands_list

        self.add_btn = QPushButton("Добавить команду", self)  # Вызов функции добавления команды
        self.add_btn.resize(200, 30)
        self.add_btn.move(320, 10)
        self.add_btn.clicked.connect(self.add_command)

        self.del_btn = QPushButton("Удалить команду", self)  # Вызов функции удаления команды
        self.del_btn.resize(200, 30)
        self.del_btn.move(320, 50)
        self.del_btn.clicked.connect(self.del_command)

    def add_command(self):  # Добавлениe команды
        global token
        global window
        message, ok_pressed = QInputDialog.getText(self, "Введите команду", "Введите команду")
        if ok_pressed:
            answer, ok_pressed = QInputDialog.getText(self, "Введите ответ", "Введите ответ")
            if ok_pressed:
                con = sqlite3.connect("db-sctb.sqlite")
                cur = con.cursor()

                if message in window.commands_dict:  # Проверка существует ли команда, если существует то перезаписываем
                    cur.execute("""DELETE FROM commands WHERE message = ?""", (message,))
                    for i in range(len(window.commands_list)):
                        if window.commands_list[i][1] == message:
                            window.commands_list.pop(i)
                            break

                cur.execute("""INSERT INTO commands(token, message, answer)
                                        VALUES(?, ?, ?)""", (token, message, answer))  # Запись новой команды в БД

                con.commit()
                con.close()

                window.commands_list.append((token, message, answer))
                window.commands_dict[message] = answer

                self.table_commands.clear()
                self.table_commands.setHorizontalHeaderItem(0, QTableWidgetItem("message"))
                self.table_commands.setHorizontalHeaderItem(1, QTableWidgetItem("answer"))
                self.table_commands.setRowCount(len(window.commands_list))
                for y in range(len(window.commands_list)):  # Заполнение таблицы новыми данными
                    for x in range(2):
                        item = QTableWidgetItem(window.commands_list[y][x + 1])
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.table_commands.setItem(y, x, item)

    def del_command(self):  # Удаление команды
        global token
        global window

        command, ok_pressed = QInputDialog.getItem(self, "Выберите команду", "Выберите команду",
                                                   tuple([x[1] for x in window.commands_list]))  # Выбор команды
        if ok_pressed:
            for i in range(len(window.commands_list)):  # Удаление команды
                if command in window.commands_list[i]:
                    window.commands_list.pop(i)
                    break
            del window.commands_dict[command]

            self.table_commands.clear()
            self.table_commands.setHorizontalHeaderItem(0, QTableWidgetItem("message"))
            self.table_commands.setHorizontalHeaderItem(1, QTableWidgetItem("answer"))
            self.table_commands.setRowCount(len(window.commands_list))
            for y in range(len(window.commands_list)):  # Заполнение таблицы новыми данными
                for x in range(2):
                    item = QTableWidgetItem(window.commands_list[y][x + 1])
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table_commands.setItem(y, x, item)

            con = sqlite3.connect("db-sctb.sqlite")
            cur = con.cursor()

            cur.execute("""DELETE FROM commands WHERE message = ?""", (command,))  # Удаление команды из БД

            con.commit()
            con.close()


def OpenWindow():  # Открытие основного окна
    global window
    app = QApplication(sys.argv)
    window = SystemControlTelegramBot()
    window.show()
    sys.exit(app.exec_())


def getAPIToken():  # Получение токена
    app = QApplication(sys.argv)
    window = ChooseApiToken()
    window.show()
    sys.exit(app.exec_())


if not os.path.isdir("tgbotfiles"):
    os.mkdir("tgbotfiles")
if not os.path.isfile("db-sctb.sqlite"):  # Создание БД, если отсутствует
    file = open("db-sctb.sqlite", "w")
    file.close()
    con = sqlite3.connect("db-sctb.sqlite")
    cur = con.cursor()

    cur.execute("""CREATE TABLE apitokens (
    token TEXT UNIQUE
               NOT NULL
               DEFAULT token
               PRIMARY KEY,
    name  TEXT NOT NULL
               DEFAULT name
    );""")

    cur.execute("""CREATE TABLE chats (
    chat_id INTEGER UNIQUE
                    NOT NULL
                    DEFAULT (12345) 
                    PRIMARY KEY,
    title   TEXT    NOT NULL
                    DEFAULT text
    );""")

    cur.execute("""CREATE TABLE messagehistory (
    token        TEXT    NOT NULL
                         DEFAULT token,
    user_id      INTEGER NOT NULL
                         DEFAULT (12345),
    chat_id      INTEGER NOT NULL
                         DEFAULT (12345),
    user_name    TEXT    NOT NULL
                         DEFAULT lastname,
    name         TEXT    NOT NULL
                         DEFAULT name,
    lastname     TEXT    NOT NULL
                         DEFAULT lastname,
    time         TEXT    NOT NULL
                         DEFAULT time,
    type         TEXT    DEFAULT text
                         NOT NULL,
    message_path TEXT    NOT NULL
                         DEFAULT [message/path]
    );""")

    cur.execute("""CREATE TABLE users (
    user_id   INTEGER PRIMARY KEY AUTOINCREMENT
                      NOT NULL
                      UNIQUE
                      DEFAULT (12345),
    user_name TEXT    NOT NULL
                      DEFAULT user_name,
    name      TEXT    NOT NULL
                      DEFAULT [name-lastname],
    lastname  TEXT    NOT NULL
                      DEFAULT lastname
    );""")

    cur.execute("""CREATE TABLE commands (
    token   TEXT NOT NULL
                 DEFAULT token,
    message TEXT NOT NULL
                 DEFAULT [/start],
    answer  TEXT DEFAULT text
                 NOT NULL
    );""")

    con.commit()
    con.close()

choosed = False
token = None
thread3 = threading.Thread(target=getAPIToken)  # Запуск потока с выбором токена
thread3.start()
thread3.join()

if choosed is False:  # Закрытие программы, если токен не выбран
    sys.exit()

bot = telebot.TeleBot(token)  # Создание бота


@bot.message_handler(content_types="text")  # Получение текстовых сообщений
def function_tg(message):
    window.new_id(message)
    window.add_text_message(message)
    window.auto_answer(message)


@bot.message_handler(
    content_types=["audio", "document", "photo", "video", "video_note", "voice", "animation",
                   "sticker"])  # Получение файлов
def function_tg(message):
    window.new_id(message)
    window.add_file_message(message)


def TelegramBot():  # Запуск бота
    bot.infinity_polling(timeout=1, long_polling_timeout=1)


window = None
thread1 = threading.Thread(target=OpenWindow)  # Создание потока с основным окном
thread2 = threading.Thread(target=TelegramBot)  # Запуск потока с ботом

thread1.start()
thread2.start()

thread1.join()
thread2.join()
