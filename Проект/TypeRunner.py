import hashlib
import sqlite3
import time
import tkinter
from random import choice
from threading import Thread
from tkinter import colorchooser

import pygame

from button import Button
from ib import InputBox
from rr import InputBox as TextIB

cfg_txt_color = '#000000'
cfg_txt_size = 60
cfg_corr_txt_color = '#00FF00'


class Core:
    def __init__(self, width, height, fps):
        self.width = width
        self.height = height
        self.fps = fps

        self.text_db = sqlite3.connect('data/texts.db').cursor()
        self.db_users = sqlite3.connect('data/users.db')
        self.cur_users = self.db_users.cursor()

        self.acc_id = -1

        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.to_menu()

        self.clock = pygame.time.Clock()

    def set_acc_id(self, cid):
        self.acc_id = cid

    def go_play(self, text='', level_mod=False, need_speed=None, need_mist=None):
        if not text:
            texts = self.text_db.execute('SELECT text FROM texts').fetchall()
            text = choice(texts)[0]

        self.iw = InputAreaWidget(self.screen, text, level_mod=level_mod, need_speed=need_speed, need_mist=need_mist)
        self.update_screen()
        self.current_widget = self.iw

    def to_menu(self):
        self.main_menu = MainMenuWidget(self.screen, self.acc_id)
        self.main_menu.go_play = False
        self.update_screen()
        self.current_widget = self.main_menu

    def go_sett(self):
        self.settings = SettingsWidget(self.screen)
        self.update_screen()
        self.current_widget = self.settings

    def go_auht(self):
        self.auth_widget = AuthWidget(self.screen, self, self.db_users)
        self.update_screen()
        self.current_widget = self.auth_widget

    def go_reg(self):
        self.reg_widget = RegWidget(self.screen, self.db_users)
        self.update_screen()
        self.current_widget = self.reg_widget

    def go_prof(self):
        self.prof_widget = ProfileWidget(self.screen, self.acc_id, self.db_users)
        self.update_screen()
        self.current_widget = self.prof_widget

    def to_lvl_map(self):
        self.lvl_map = LevelMap(self.screen)
        self.update_screen()
        self.current_widget = self.lvl_map

    def start_game(self):
        self.flag_stop_game_thread = False
        self.game_run_thread = Thread(target=self._game_run).run()

    def add_stats_to_db(self, speed, rating):
        if self.acc_id != -1:
            self.cur_users.execute("""UPDATE stats
                                SET count = count + 1
                                WHERE id = ?""", (self.acc_id,))

            self.cur_users.execute("""UPDATE stats
                                SET speed_avg = (speed_avg * count + ?) * count
                                WHERE id = ?""", (speed, self.acc_id))

            self.cur_users.execute("""UPDATE stats
                                SET rating_avg = (rating_avg * count + ?) * count
                                WHERE id = ?""", (rating, self.acc_id))
            old_speed = self.cur_users.execute("""SELECT speed_best FROM stats
                                            WHERE id = ?""", (self.acc_id,)).fetchone()[0]
            new_speed = max(speed, old_speed)
            self.cur_users.execute("""UPDATE stats
                                SET speed_best = ?
                                WHERE id = ?""", (new_speed, self.acc_id))

            old_rating = self.cur_users.execute("""SELECT rating_best FROM stats
                                             WHERE id = ?""", (self.acc_id,)).fetchone()[0]
            new_rating = max(rating, old_rating)
            self.cur_users.execute("""UPDATE stats
                                SET rating_best = ?
                                WHERE id = ?""", (new_rating, self.acc_id))
            self.db_users.commit()

    def _game_run(self):
        bg = pygame.image.load('background.png').convert_alpha()
        while not self.flag_stop_game_thread:
            self.screen.blit(bg, (0, 0))
            self.event_manager()
            if type(self.current_widget) == InputAreaWidget:
                self.iw.count_speed()
                if self.iw.ms.rect.x >= self.iw.pl.rect.x - 50:
                    self.iw.is_started = False
                    self.add_stats_to_db(self.iw.speed, self.iw.speed // (self.iw.mistakes + 1))
                    self.current_widget = DefeatWidget(self.screen, self.iw.mistakes)
                    self.update_screen()
                    self.current_widget.show()
                if self.iw.go_menu:
                    self.iw.go_menu = False
                    self.to_menu()
            if type(self.current_widget) == MainMenuWidget:
                self.main_menu.show()
                if self.main_menu.go_play:
                    self.main_menu.go_play = False
                    self.go_play()
                if self.main_menu.go_sett:
                    self.go_sett()
                if self.main_menu.go_auth:
                    self.go_auht()
                if self.main_menu.go_prof:
                    self.go_prof()
                if self.main_menu.to_lvl_map:
                    self.to_lvl_map()
            if type(self.current_widget) in [WinWidget, DefeatWidget]:
                self.current_widget.show()
                if self.current_widget.go_menu:
                    self.to_menu()
                elif self.current_widget.restart:
                    self.go_play()
            if type(self.current_widget) == SettingsWidget:
                if self.current_widget.go_menu:
                    self.current_widget.go_menu = False
                    self.to_menu()

            if type(self.current_widget) == AuthWidget:
                if self.current_widget.go_reg:
                    self.current_widget.go_reg = False
                    self.go_reg()
                if self.current_widget.go_menu:
                    self.current_widget.go_menu = False
                    self.to_menu()

            if type(self.current_widget) == RegWidget:
                if self.current_widget.go_menu:
                    self.to_menu()
                if self.current_widget.go_auth:
                    self.go_auht()

            if type(self.current_widget) == ProfileWidget:
                if self.current_widget.log_out:
                    self.acc_id = -1
                    self.to_menu()
                    continue
                if self.current_widget.go_menu:
                    self.to_menu()

            if type(self.current_widget) == LevelMap:
                if self.current_widget.go_menu:
                    self.to_menu()
            self.current_widget.show()
            self.clock.tick(self.fps)
            pygame.display.flip()

    def event_manager(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.flag_stop_game_thread = pygame.quit()

            if type(self.current_widget) == InputAreaWidget:
                if event.type == pygame.KEYDOWN:
                    if event.unicode == self.iw.corr_text[len(self.iw.right_text)]:
                        if not self.iw.is_started:
                            self.iw.is_started = True
                            self.iw.start_time = time.time()

                        self.iw.right_text += event.unicode
                        if len(self.iw.right_text) == len(self.iw.corr_text):
                            self.iw.is_started = False
                            if not self.iw.level_mod:
                                self.add_stats_to_db(self.iw.speed, self.iw.speed // (self.iw.mistakes + 1))
                                self.current_widget = WinWidget(self.screen, self.iw.mistakes)
                                self.update_screen()
                                self.current_widget.show()
                            else:
                                print(self.iw.mistakes <= self.iw.need_mist)
                                print(self.iw.speed >= self.iw.need_speed)
                                if self.iw.mistakes <= self.iw.need_mist and self.iw.get_speed() >= self.iw.need_speed:
                                    self.add_stats_to_db(self.iw.speed, self.iw.speed // (self.iw.mistakes + 1))
                                    self.current_widget = WinWidget(self.screen, self.iw.mistakes)
                                    self.update_screen()
                                    self.current_widget.show()
                                else:
                                    print('2')
                                    if self.iw.mistakes > self.iw.need_mist:
                                        self.add_stats_to_db(self.iw.speed, self.iw.speed // (self.iw.mistakes + 1))
                                        self.current_widget = DefeatWidget(self.screen, self.iw.mistakes, message='Ты допустил слишком много ошибок.')
                                        self.update_screen()
                                        self.current_widget.show()
                                    elif self.iw.get_speed() < self.iw.need_speed:
                                        self.add_stats_to_db(self.iw.speed, self.iw.speed // (self.iw.mistakes + 1))
                                        self.current_widget = DefeatWidget(self.screen, self.iw.mistakes,
                                                                           message='Ты слишком медленный')
                                        self.update_screen()
                                        self.current_widget.show()
                    else:
                        if event.unicode.isalpha():
                            self.iw.mistakes += 1

            if type(self.current_widget) == SettingsWidget:
                self.current_widget.txt_size_ib.handle_event(event)

            if type(self.current_widget) == AuthWidget:
                self.current_widget.login_ib.handle_event(event)
                self.current_widget.password_ib.handle_event(event)

            if type(self.current_widget) == RegWidget:
                self.current_widget.login_ib.handle_event(event)
                self.current_widget.password_ib.handle_event(event)
                self.current_widget.repeat_ib.handle_event(event)

            if type(self.current_widget) == LevelMap:
                if event.type == pygame.MOUSEBUTTONUP:
                    x, y = event.pos
                    try:
                        for btn in range(len(self.current_widget.buttons)):
                            if self.current_widget.buttons[btn][0] <= x <= self.current_widget.buttons[btn][2] and \
                                    self.current_widget.buttons[btn][1] <= y <= self.current_widget.buttons[btn][3]:
                                text = self.text_db.execute('''SELECT text FROM levels WHERE number=?''',
                                                            (btn + 1,)).fetchone()[0]
                                mist = self.text_db.execute('''SELECT mistakes FROM levels WHERE number=?''',
                                                            (btn + 1,)).fetchone()[0]
                                speed = self.text_db.execute('''SELECT speed FROM levels WHERE number=?''',
                                                            (btn + 1,)).fetchone()[0]
                                self.go_play(text=text, level_mod=True, need_mist=mist, need_speed=speed)
                    except:
                        pass

    def update_screen(self):
        self.screen.fill('grey')


class LevelMap:
    def __init__(self, screen):
        self.screen = screen
        self.back_button_im = pygame.image.load('back.png').convert_alpha()
        self.back_button = Button(35, 35, self.back_button_im, 1)
        self.go_menu = False
        self.buttons = []
        self.im = pygame.image.load('rect.png').convert_alpha()
        self.f = pygame.font.Font(None, 150)

        self.create_buttons()

    def create_buttons(self):
        db = sqlite3.connect('data/texts.db').cursor()
        level_list = db.execute('''SELECT number FROM levels''').fetchall()

        for x in level_list:
            btn = [100 + 120 * len(self.buttons), 200 + 200 * (len(self.buttons) // 7)]
            btn.append(btn[0] + 100)
            btn.append(btn[1] + 100)
            txt = str(x[0])
            btn.append(txt)
            self.buttons.append(btn)
            # im = f.render(txt, True, 'red')

    def show(self):
        for btn in self.buttons:
            self.screen.blit(self.im, [btn[0], btn[1]])
            self.screen.blit(self.f.render(btn[-1], True, 'white'), [btn[0] + 25, btn[1]])
        if self.back_button.draw(self.screen):
            self.go_menu = True


class InputAreaWidget:
    def __init__(self, screen, text, level_mod=False, need_speed=None, need_mist=None):
        self.screen = screen

        self.level_mod = level_mod
        if self.level_mod:
            self.need_speed = need_speed
            self.need_mist = need_mist

        self.corr_text = text.strip()
        self.word = self.corr_text.split(' ')
        self.line = 0
        self.text_lines = ['']
        self.right_text = ''
        self.mistakes = 0

        self.is_started = False

        self.fbg = pygame.image.load('textbg.png').convert_alpha()

        self.font_size = cfg_txt_size
        self.font_color = cfg_txt_color
        self.font_color_right = cfg_corr_txt_color
        self.font = pygame.font.Font(None, self.font_size)

        # self.pam = PlayerAndMonsterWidget(self.screen)
        self.pam = pygame.sprite.Group()
        self.ms = Monster(100, 670, self.pam)
        self.pl = Player(900, 670, self.pam)

        self.pam.add(self.ms, self.pl)

        self.start_time = None
        self.speed = 0

        self.back_button_im = pygame.image.load('back.png').convert_alpha()
        self.back_button = Button(35, 35, self.back_button_im, 1)
        self.go_menu = False

    def get_speed(self):
        return len(self.right_text) / (time.time() - self.start_time) * 60

    def count_speed(self):
        if not self.level_mod:
            try:
                self.speed = len(self.right_text) / (time.time() - self.start_time) * 60
                if self.speed > 135:
                    self.speed = -1
                elif self.speed < 110:
                    self.speed = 2
                elif self.speed < 100:
                    self.speed = 3
                else:
                    self.speed = 1
            except Exception as e:
                self.speed = 0
        else:
            try:
                self.speed = len(self.right_text) / (time.time() - self.start_time) * 60
                if self.speed > self.need_speed * 0.85:
                    self.speed = -1
                elif self.speed < self.need_speed * 0.7:
                    self.speed = 2
                elif self.speed < self.need_speed * 0.5:
                    self.speed = 3
                else:
                    self.speed = 1
            except Exception as e:
                self.speed = 0

    # def show(self):
    #     l1 = self.font.render('Алдыващроа', True, cfg_txt_color)
    #     l2 = self.font.render('Алдыващроа', True, cfg_corr_txt_color)
    #
    #     self.screen.blit(l1, [63, 150])
    #     self.screen.blit(l2, [63, 150])

    def show(self):
        back_line = 0
        back_text_line = ''
        self.screen.blit(self.fbg, (50, 150))
        f = pygame.font.Font(None, 68)
        if not self.level_mod:
            try:
                self.screen.blit(f.render(
                    f'Сивмолов в минуту: {int(len(self.right_text) / (time.time() - self.start_time) * 60)}', True,
                    'white'), [500, 50])
            except Exception as e:
                self.screen.blit(f.render(
                    f'Сивмолов в минуту:{0}', True, 'white'), [500, 50])
            self.screen.blit(f.render(f'Ошибки: {self.mistakes}', True, 'white'), [150, 50])
        else:
            try:
                spd = int(len(self.right_text) / (time.time() - self.start_time) * 60)

                self.screen.blit(f.render(
                    f'Сивмолов в минуту: {spd} / {self.need_speed}', True,
                    'white'), [500, 50])
            except Exception as e:
                self.screen.blit(f.render(
                    f'Сивмолов в минуту:{0}', True, 'white'), [500, 50])
            self.screen.blit(f.render(f'Ошибки: {self.mistakes} / {self.need_mist}', True, 'white'), [150, 50])
        spaces = 0
        for c in self.corr_text:
            back_text_line += c

            if c == ' ':
                spaces += 1

            # if 1100 - self.font.render(back_text_line, False, 'red').get_rect()[2] <= 15 * cfg_txt_size / 2.4\
            #         and back_text_line[-1] == ' ':
            if 1100 - len(back_text_line) * cfg_txt_size / 2.4 <= len(self.word[spaces]) * cfg_txt_size / 2.4 \
                    and back_text_line[-1] == ' ':
                plane = self.font.render(back_text_line, True, self.font_color)
                self.screen.blit(plane, (63, 55 * (1 + back_line) + 112))

                back_text_line = ''
                back_line += 1
            plane = self.font.render(back_text_line, True, self.font_color)
            self.screen.blit(plane, (63, 55 * (1 + back_line) + 112))

        back_text_line = ''
        back_line = 0
        spaces = 0

        for c in self.right_text:
            back_text_line += c

            if c == ' ':
                spaces += 1

            # if 1100 - self.font.render(back_text_line, False, 'red').get_rect()[2] <= 15 * cfg_txt_size / 2.4\
            #         and back_text_line[-1] == ' ':
            if 1100 - len(back_text_line) * cfg_txt_size / 2.4 <= len(self.word[spaces]) * cfg_txt_size / 2.4 \
                    and back_text_line[-1] == ' ':
                plane = self.font.render(back_text_line, True, self.font_color_right)
                self.screen.blit(plane, (63, 55 * (1 + back_line) + 112))

                back_text_line = ''
                back_line += 1

        plane = self.font.render(back_text_line, True, self.font_color_right)
        self.screen.blit(plane, (63, 55 * (1 + back_line) + 112))

        # for i in range(len(self.text_lines)):
        #     plane = self.font.render(self.text_lines[i], True, self.font_color_right)
        #     self.screen.blit(plane, (63, 55 * (1 + i) + 112))

        if self.speed != 0:
            self.pam.update(self.speed)
        # self.pam.clear(self.screen, pygame.image.load('background.png').convert_alpha())

        self.pam.draw(self.screen)

        if self.back_button.draw(self.screen):
            self.go_menu = True

        # self.pam.show(self.speed)
        # self.pam.clear()


class Monster(pygame.sprite.Sprite):
    images = [pygame.image.load("monster0.png").convert_alpha(), pygame.image.load("monster1.png").convert_alpha(),
              pygame.image.load("monster2.png").convert_alpha()]

    def __init__(self, x, y, *group):
        super().__init__(*group)
        self.image = Monster.images[0]
        self.k = 0
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self, speed):
        if self.k % 4:
            self.image = Monster.images[self.k % 3]
        self.k += 1
        if self.rect.x <= -12 and speed < 0:
            speed = 0

        self.rect = self.rect.move(speed, 0)

    def get_x(self):
        return self.rect.x


class Player(pygame.sprite.Sprite):
    images = [pygame.image.load("player0.png").convert_alpha(), pygame.image.load("player1.png").convert_alpha(),
              pygame.image.load("player2.png").convert_alpha()]

    def __init__(self, x, y, *group):
        super().__init__(*group)
        self.image = Player.images[0]
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.k = 0

    def update(self, speed):
        if self.k % 2:
            self.image = Player.images[self.k % 3]
        self.k += 1
        self.rect = self.rect.move(0, 0)

    def get_x(self):
        return self.rect.x


class DefeatWidget:
    def __init__(self, screen, mistakes, message='Монстр догнал тебя!'):
        self.mistakes = mistakes
        self.screen = screen
        self.message = message
        self.restart_button_im = pygame.image.load('repeat.png').convert_alpha()
        self.restart_button = Button(200, 400, self.restart_button_im, 1)
        self.mm_button = Button(900, 400, pygame.image.load('home.png').convert_alpha(), 1)
        self.go_menu = False
        self.restart = False

    def show(self):
        font_color = 'red'
        font = pygame.font.Font(None, 100)
        plane = font.render(self.message, True, font_color)
        self.screen.blit(plane, (200, 200))
        font_color = 'black'
        font = pygame.font.Font(None, 75)
        plane = font.render(f'Количество допущеных ошибок: {self.mistakes}', True, font_color)
        self.screen.blit(plane, (200, 300))
        if self.mm_button.draw(self.screen):
            self.go_menu = True
        if self.restart_button.draw(self.screen):
            self.restart = True


class WinWidget:
    def __init__(self, screen, mistakes):
        self.screen = screen
        self.mistakes = mistakes
        self.restart_button_im = pygame.image.load('repeat.png').convert_alpha()
        self.restart_button = Button(200, 400, self.restart_button_im, 1)
        self.mm_button_im = pygame.image.load('menu.png').convert_alpha()
        self.mm_button = Button(300, 400, self.mm_button_im, 1)
        self.go_menu = False
        self.restart = False

    def show(self):
        font_color = 'green'
        font = pygame.font.Font(None, 100)
        plane = font.render('Ты убежал от монстра', True, font_color)
        self.screen.blit(plane, (200, 200))
        font_color = 'black'
        font = pygame.font.Font(None, 75)
        plane = font.render(f'Количество допущеных ошибок: {self.mistakes}', True, font_color)
        self.screen.blit(plane, (200, 300))
        if self.mm_button.draw(self.screen):
            self.go_menu = True
        if self.restart_button.draw(self.screen):
            self.restart = True


class MainMenuWidget:
    def __init__(self, screen, user_id):
        self.user_id = user_id
        font_color = 'red'
        font = pygame.font.Font(None, 200)
        self.plane = pygame.image.load('TypeRunner.png').convert_alpha()
        self.screen = screen
        self.setting_button_im = pygame.image.load('settings.png').convert_alpha()
        self.setting_button = Button(900, 500, self.setting_button_im, 1)

        self.lvl_map_im = pygame.image.load('level_map.png').convert_alpha()
        self.lvl_map_button = Button(500, 300, self.lvl_map_im, 2)
        self.start_button_im = pygame.image.load('play.png').convert_alpha()
        self.start_button = Button(500, 300, self.start_button_im, 2)

        self.current_btn = 0

        self.btn_left_im = pygame.image.load('rect.png').convert_alpha()
        self.btn_left = Button(100, 300, self.btn_left_im, 1)
        self.btn_right_im = pygame.image.load('rect.png').convert_alpha()
        self.btn_right = Button(1000, 300, self.btn_right_im, 1)

        self.acc_button_im = pygame.image.load('acc.png').convert_alpha()
        self.acc_button = Button(200, 500, self.acc_button_im, 1)
        self.go_play = False
        self.go_auth = False
        self.go_sett = False
        self.go_prof = False

        self.to_lvl_map = False

    def show(self):
        if self.current_btn == 0:
            if self.start_button.draw(self.screen):
                self.go_play = True
        if self.current_btn == 1:
            if self.lvl_map_button.draw(self.screen):
                self.to_lvl_map = True

        if self.btn_right.draw(self.screen):
            self.current_btn = (self.current_btn + 1) % 2
        if self.btn_left.draw(self.screen):
            self.current_btn = (self.current_btn - 1) % 2

        if self.setting_button.draw(self.screen):
            self.go_sett = True
        self.screen.blit(self.plane, (200, 150))
        if self.acc_button.draw(self.screen):
            if self.user_id == -1:
                self.go_auth = True
            else:
                self.go_prof = True


class AuthWidget:
    def __init__(self, screen, core, udb):
        self.cur = udb.cursor()
        self.udb = udb
        self.core = core
        self.screen = screen
        self.login_ib = TextIB(screen, 550, 250, 240, 32)
        self.password_ib = TextIB(screen, 550, 325, 240, 32)
        self.reg_btn_im = pygame.image.load('reg.png').convert_alpha()
        self.reg_btn = Button(625, 475, self.reg_btn_im, 1)
        self.login_btn_im = pygame.image.load('accept.png').convert_alpha()
        self.login_btn = Button(425, 475, self.login_btn_im, 1)
        self.go_reg = False
        self.go_menu = False

        self.f = pygame.font.Font(None, 50)
        self.ef = pygame.font.Font(None, 40)
        self.err_msg = ''

    def show(self):
        self.screen.blit(self.f.render(self.err_msg, True, 'red'), (475, 175))
        self.screen.blit(self.f.render('Логин:', True, 'black'), (350, 250))
        self.screen.blit(self.f.render('Пароль:', True, 'black'), (350, 325))
        self.login_ib.draw(self.screen)
        self.password_ib.draw(self.screen)
        if self.reg_btn.draw(self.screen):
            self.go_reg = True
        if self.login_btn.draw(self.screen):
            self.login()

    def login(self):
        login = self.login_ib.text
        password = self.password_ib.text

        if not login:
            self.err_msg = 'Введите логин'
            return
        elif not password:
            self.err_msg = 'Ввделите пароль'
            return
        elif not self.check_login(login):
            self.err_msg = 'Логин не существует'
            return
        else:
            if self.check_password(login, password):
                self.core.set_acc_id(
                    self.cur.execute('''SELECT id FROM auth_data WHERE login=?''', (login,)).fetchone()[0])

                self.go_menu = True
            else:
                self.err_msg = 'Неверный логин или пароль'

    def check_login(self, login):
        log = self.cur.execute('''SELECT login FROM auth_data WHERE login=?''', (login,)).fetchall()
        return bool(log)

    def check_password(self, login, password):
        correct_hash = self.cur.execute('''SELECT password FROM auth_data WHERE login=?''',
                                        (login,)).fetchone()
        hash = hashlib.md5(password.encode())
        hex_hash = hash.hexdigest()
        if hex_hash == correct_hash[0]:
            return True
        else:
            return False


class RegWidget:
    def __init__(self, screen, udb):
        self.screen = screen
        self.login_ib = TextIB(screen, 550, 250, 240, 32)
        self.password_ib = TextIB(screen, 550, 325, 240, 32)
        self.repeat_ib = TextIB(screen, 550, 400, 240, 32)
        self.signin_btn_im = pygame.image.load('accept.png').convert_alpha()
        self.signin_btn = Button(425, 475, self.signin_btn_im, 1)
        self.login_btn_im = pygame.image.load('login.png').convert_alpha()
        self.login_btn = Button(625, 475, self.login_btn_im, 1)
        self.udb = udb
        self.cur = self.udb.cursor()

        self.f = pygame.font.Font(None, 50)

        self.err_msg = ''

        self.go_menu = False
        self.go_auth = False

    def show(self):
        self.screen.blit(self.f.render(self.err_msg, True, 'red'), (475, 175))
        self.screen.blit(self.f.render('Логин:', True, 'black'), (350, 250))
        self.screen.blit(self.f.render('Пароль:', True, 'black'), (350, 325))
        self.screen.blit(self.f.render('Повтор:', True, 'black'), (350, 400))
        self.login_ib.draw(self.screen)
        self.password_ib.draw(self.screen)
        self.repeat_ib.draw(self.screen)
        if self.signin_btn.draw(self.screen):
            self.reg()
        if self.login_btn.draw(self.screen):
            self.go_auth = True

    def reg(self):
        login = self.login_ib.text
        password = self.password_ib.text
        repeat = self.repeat_ib.text
        if not login:
            self.err_msg = 'Введите логин'
            return
        if not password:
            self.err_msg = 'Ввделите пароль'
            return
        if not repeat:
            self.err_msg = 'Повторите пароль'
            return
        if self.check_login(login):
            self.err_msg = 'Логин уже занят'
            return
        if password != repeat:
            self.err_msg = 'Пароли не совпадают'
            return
        id = self.get_user_id()
        hash = hashlib.md5(password.encode())
        hex_hash = hash.hexdigest()
        self.cur.execute("""INSERT INTO auth_data(id, login, password)
            VALUES(?, ?, ?)""", (id, login, hex_hash))
        self.cur.execute("""INSERT INTO stats(id, count, speed_avg, speed_best, rating_avg, rating_best)
                    VALUES(?, ?, ?, ?, ?, ?)""", (id, 0, 0, 0, 0, 0))
        self.cur.execute("""INSERT INTO avatars(id, path)
                            VALUES(?, ?)""", (id, 'data/avatars/default.png'))
        self.udb.commit()
        self.go_menu = True

    def get_user_id(self):
        return self.cur.execute("""SELECT id FROM auth_data
            ORDER BY id DESC LIMIT 1""").fetchone()[0] + 1

    def check_login(self, login):
        log = self.cur.execute('''SELECT login FROM auth_data WHERE login=?''', (login,)).fetchall()
        return bool(log)


class SettingsWidget:
    def __init__(self, screen):
        self.screen = screen
        self.change_color_button_im = pygame.image.load('pallete.png').convert_alpha()
        self.change_color_button = Button(670, 200, self.change_color_button_im, 1)
        self.change_color_button_corr = Button(670, 350, self.change_color_button_im, 1)
        self.mm_button_im = pygame.image.load('home.png').convert_alpha()
        self.mm_button = Button(35, 35, self.mm_button_im, 1)
        self.txt_size_ib = InputBox(self.screen, 670, 500, 100, 100, text=str(cfg_txt_size))
        self.go_menu = False

    def show(self):
        global cfg_txt_color, cfg_txt_size, cfg_corr_txt_color
        if self.change_color_button.draw(self.screen):
            r = tkinter.Tk()
            r.withdraw()
            cfg_txt_color = colorchooser.askcolor()[1]
        if self.change_color_button_corr.draw(self.screen):
            r = tkinter.Tk()
            r.withdraw()
            cfg_corr_txt_color = colorchooser.askcolor()[1]

        if self.mm_button.draw(self.screen):
            self.go_menu = True

        self.txt_size_ib.draw(self.screen)
        if self.txt_size_ib.value_changed:
            self.txt_size_ib.value_changed = False
            cfg_txt_size = int(self.txt_size_ib.get_text())

        font = pygame.font.Font(None, 55)
        self.screen.blit(font.render('Цвет текста:', True, 'black'), (150, 250))
        self.screen.blit(font.render('Цвет правильного текста:', True, 'black'), (150, 400))
        self.screen.blit(font.render('Размер текста:', True, 'black'), (150, 550))


class ProfileWidget:
    def __init__(self, screen, cid, udb):
        self.screen = screen
        self.udb = udb
        self.cur = self.udb.cursor()
        self.id = cid
        self.name = self.cur.execute('''SELECT login FROM auth_data WHERE id=?''', (self.id,)).fetchone()[0]
        self.avatar_path = self.cur.execute('''SELECT path FROM avatars WHERE id=?''', (self.id,)).fetchone()[0]
        self.speed_best = self.cur.execute('''SELECT speed_best FROM stats WHERE id=?''', (self.id,)).fetchone()[0]
        self.speed_avg = self.cur.execute('''SELECT speed_avg FROM stats WHERE id=?''', (self.id,)).fetchone()[0]
        self.rating_avg = self.cur.execute('''SELECT rating_avg FROM stats WHERE id=?''', (self.id,)).fetchone()[0]
        self.avatar = pygame.image.load(self.avatar_path).convert_alpha()
        self.avatar = pygame.transform.scale(self.avatar, (150, 150))
        self.back_button_im = pygame.image.load('back.png').convert_alpha()
        self.back_button = Button(50, 50, self.back_button_im, 1)

        self.go_menu = False

        self.log_out_btn_im = pygame.image.load('off.png').convert_alpha()
        self.log_out_btn = Button(900, 500, self.log_out_btn_im, 1)
        self.log_out = False

    def show(self):
        self.screen.blit(self.avatar, (100, 200))
        f = pygame.font.Font(None, 50)
        self.screen.blit(f.render(str(self.name), True, 'black'), (125, 375))
        self.screen.blit(f.render('Лучшая скорость:', True, 'black'), (300, 275))
        self.screen.blit(f.render(str(self.speed_best), True, 'black'), (700, 275))
        self.screen.blit(f.render('Средняя скорость:', True, 'black'), (300, 375))
        self.screen.blit(f.render(str(self.speed_avg), True, 'black'), (700, 375))
        self.screen.blit(f.render('Средний рейтинг:', True, 'black'), (300, 475))
        self.screen.blit(f.render(str(self.rating_avg), True, 'black'), (700, 475))

        if self.back_button.draw(self.screen):
            self.go_menu = True
        if self.log_out_btn.draw(self.screen):
            self.log_out = True

class Button:
	def __init__(self, x, y, image, scale):
		width = image.get_width()
		height = image.get_height()
		self.image = pygame.transform.scale(image, (int(width * scale), int(height * scale)))
		self.rect = self.image.get_rect()
		self.rect.topleft = (x, y)
		self.clicked = False

	def draw(self, surface):
		action = False
		#get mouse position
		pos = pygame.mouse.get_pos()

		#check mouseover and clicked conditions
		if self.rect.collidepoint(pos):
			if pygame.mouse.get_pressed()[0] == 1 and self.clicked == False:
				self.clicked = True
				action = True

		if pygame.mouse.get_pressed()[0] == 0:
			self.clicked = False

		#draw button on screen
		surface.blit(self.image, (self.rect.x, self.rect.y))

		return action

class InputBox:

    def __init__(self, screen, x, y, w, h, text=''):
        self.screen = screen
        self.rect = pygame.Rect(x, y, w, h)
        self.FONT = pygame.font.Font(None, 52)
        self.COLOR_INACTIVE = 'black'
        self.COLOR_ACTIVE =   'grey'
        self.color =          'black'
        self.text = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False
        self.value_changed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
                self.text = ''
                self._set_value()
            else:
                self.active = False
                self._check_value()
                self._set_value()
            # Change the current color of the input box.
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                # if event.key == pygame.K_RETURN:
                #     print(self.text)
                #     self.text = ''
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode.isdigit():
                        self.text += event.unicode
                # Re-render the text.
                self._set_value()

class TextIB:
    def __init__(self, screen, x, y, w, h, text=''):
        self.screen = screen
        self.rect = pygame.Rect(x, y, w, h)
        self.FONT = pygame.font.Font(None, 32)
        self.COLOR_INACTIVE = pygame.Color('lightskyblue3')
        self.COLOR_ACTIVE = pygame.Color('dodgerblue2')
        self.color = self.COLOR_INACTIVE
        self.text = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    print(self.text)
                    self.text = ''
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = self.FONT.render(self.text, True, self.color)

    def update(self):
        # Resize the box if the text is too long.
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)

c = Core(1200, 800, 20)
c.start_game()
