import customtkinter as ctk
import time
import threading
import requests
import pygame
import os
import random
import sqlite3
import ctypes
from datetime import datetime, date

# --- ТВОИ НАСТРОЙКИ ---
BOT_TOKEN = "8600824286:AAHUvA1Q9AQ0SgkbjX7AlJzvKly2bJ6hSe8"
CHAT_ID = "1215866388"
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
KEEP_AWAKE = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED

ctk.set_appearance_mode("dark")

class FocusOS(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FOCUS OS // v10.0")
        self.geometry("480x880")
        self.resizable(False, False)
        
        self.after(200, self.force_dark_titlebar)

        self.is_running = False
        self.seconds_left = 0
        self.total_session_time = 0
        self.total_duration = 0
        self.is_muted = False
        self.current_volume = 0.5
        
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.current_volume)
        
        self.init_db()
        self.build_ui()

    def force_dark_titlebar(self):
        try:
            HWND = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND, 20, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int(2)))
        except Exception: pass

    def init_db(self):
        self.conn = sqlite3.connect('focus_log.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, duration INTEGER, task_name TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS quests (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, is_completed INTEGER DEFAULT 0)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS user_stats (id INTEGER PRIMARY KEY, xp INTEGER)')
        
        # БЕЗОПАСНАЯ МИГРАЦИЯ БАЗЫ ДАННЫХ (Добавляем стрики)
        try: self.cursor.execute('ALTER TABLE user_stats ADD COLUMN last_session_date TEXT DEFAULT ""')
        except: pass
        try: self.cursor.execute('ALTER TABLE user_stats ADD COLUMN current_streak INTEGER DEFAULT 0')
        except: pass

        self.cursor.execute('SELECT xp FROM user_stats WHERE id = 1')
        if not self.cursor.fetchone():
            self.cursor.execute('INSERT INTO user_stats (id, xp, last_session_date, current_streak) VALUES (1, 0, "", 0)')
        self.conn.commit()

    # --- ЛОГИКА ГЕЙМИФИКАЦИИ ---
    def get_rank(self, xp):
        if xp <= 150: return "Goldfish (Lvl 1)"
        elif xp <= 500: return "Watcher (Lvl 2)"
        elif xp <= 1200: return "Hunter (Lvl 3)"
        elif xp <= 2500: return "Strategist (Lvl 4)"
        else: return "Flow Archon (Lvl 5)"

    def get_percentile(self, minutes_today):
        if minutes_today < 30: return "Bottom 50% (Distracted)"
        elif minutes_today < 60: return "Top 50% (Average)"
        elif minutes_today < 120: return "Top 30% (Focused)"
        elif minutes_today < 240: return "Top 10% (Professional)"
        elif minutes_today < 300: return "Top 5% (Elite)"
        else: return "Top 1% (God Mode)"

    def update_streak(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute('SELECT last_session_date, current_streak FROM user_stats WHERE id = 1')
        row = self.cursor.fetchone()
        last_date_str = row[0]
        streak = row[1] if row[1] else 0

        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            today_date = datetime.strptime(today_str, "%Y-%m-%d").date()
            diff = (today_date - last_date).days
            
            if diff == 1: streak += 1 # Следующий день = +1 к стрику
            elif diff > 1: streak = 1 # Пропуск дня = стрик сгорел
            # Если diff == 0 (тот же день), стрик не меняется
        else:
            streak = 1 # Первая сессия в жизни
            
        self.cursor.execute('UPDATE user_stats SET last_session_date = ?, current_streak = ? WHERE id = 1', (today_str, streak))
        self.conn.commit()

    def get_xp(self):
        self.cursor.execute('SELECT xp FROM user_stats WHERE id = 1')
        return self.cursor.fetchone()[0]

    def add_xp(self, amount):
        new_xp = self.get_xp() + amount
        self.cursor.execute('UPDATE user_stats SET xp = ? WHERE id = 1', (new_xp,))
        self.conn.commit()
        return new_xp

    def get_today_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT SUM(duration) FROM sessions WHERE date LIKE ?", (today + '%',))
        res = self.cursor.fetchone()[0]
        return res if res else 0

    def build_ui(self):
        self.tabview = ctk.CTkTabview(self, width=440, height=830, fg_color="#0a0a0a",
                                      segmented_button_selected_color="#003300",
                                      segmented_button_selected_hover_color="#005500",
                                      segmented_button_unselected_color="#121212")
        self.tabview.pack(pady=10, padx=10, expand=True, fill="both")

        self.tab_main = self.tabview.add("⚡ TERMINAL")
        self.tab_quests = self.tabview.add("🏆 QUESTS")
        self.tab_profile = self.tabview.add("👤 PROFILE")
        self.tab_hist = self.tabview.add("📊 HISTORY")

        # ==================== TERMINAL ====================
        self.header = ctk.CTkLabel(self.tab_main, text="F L O W   M O D E", font=("Courier", 26, "bold"), text_color="#00FF00")
        self.header.pack(pady=10)

        self.task_combo = ctk.CTkComboBox(self.tab_main, width=380, height=40, font=("Courier", 14), 
                                          fg_color="#121212", border_color="#00FF00", text_color="#FFFFFF",
                                          button_color="#00FF00", button_hover_color="#00AA00",
                                          dropdown_fg_color="#121212", dropdown_text_color="#00FF00", dropdown_hover_color="#003300")
        self.task_combo.pack(pady=5)

        self.manual_time_entry = ctk.CTkEntry(self.tab_main, width=100, font=("Courier", 20, "bold"), justify="center", fg_color="#121212", border_color="#00FF00", text_color="#00FF00")
        self.manual_time_entry.insert(0, "120")
        self.manual_time_entry.pack(pady=(15, 5))
        self.manual_time_entry.bind("<KeyRelease>", self.on_entry_change)

        self.preset_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.preset_frame.pack(pady=5)
        btn_style = {"fg_color": "transparent", "border_width": 1, "border_color": "#00FF00", "text_color": "#00FF00", "hover_color": "#003300", "width": 60}
        ctk.CTkButton(self.preset_frame, text="+5m", command=lambda: self.add_time(5), **btn_style).grid(row=0, column=0, padx=5)
        ctk.CTkButton(self.preset_frame, text="+25m", command=lambda: self.add_time(25), **btn_style).grid(row=0, column=1, padx=5)
        ctk.CTkButton(self.preset_frame, text="+60m", command=lambda: self.add_time(60), **btn_style).grid(row=0, column=2, padx=5)
        ctk.CTkButton(self.preset_frame, text="Reset", width=60, fg_color="#1a1a1a", border_color="#FF0000", border_width=1, text_color="#FF0000", hover_color="#330000", command=self.reset_time).grid(row=0, column=3, padx=5)

        self.timer_display = ctk.CTkLabel(self.tab_main, text="120:00", font=("Courier", 65, "bold"), text_color="#FFFFFF")
        self.timer_display.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.tab_main, width=380, height=6, progress_color="#00FF00", fg_color="#1a1a1a")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.start_btn = ctk.CTkButton(self.tab_main, text="[ INITIATE FLOW ]", command=self.start_focus, fg_color="transparent", border_width=2, border_color="#00FF00", text_color="#00FF00", hover_color="#003300", height=45, width=380)
        self.start_btn.pack(pady=5)

        self.stop_btn = ctk.CTkButton(self.tab_main, text="[ ABORT SESSION ]", command=self.stop_focus, fg_color="transparent", border_width=2, border_color="#FF0000", text_color="#FF0000", hover_color="#330000", state="disabled", height=40, width=380)
        self.stop_btn.pack(pady=5)

        self.audio_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.audio_frame.pack(pady=5)
        self.mute_btn = ctk.CTkButton(self.audio_frame, text="🔊 MUTE", command=self.toggle_mute, fg_color="transparent", text_color="#00FF00", border_width=1, border_color="#00FF00", width=80)
        self.mute_btn.grid(row=0, column=0, padx=10)
        self.vol_slider = ctk.CTkSlider(self.audio_frame, from_=0.0, to=1.0, width=200, command=self.change_volume, button_color="#00FF00", progress_color="#00FF00")
        self.vol_slider.set(self.current_volume)
        self.vol_slider.grid(row=0, column=1, padx=10)

        self.log_box = ctk.CTkTextbox(self.tab_main, width=380, height=70, font=("Courier", 11), fg_color="#050505", text_color="#00FF00", border_width=1, border_color="#1a1a1a")
        self.log_box.pack(pady=10)
        self.log_box.configure(state="disabled")

        # ==================== QUESTS ====================
        self.q_lvl_label = ctk.CTkLabel(self.tab_quests, text="LEVEL 1", font=("Courier", 24, "bold"), text_color="#FFD700")
        self.q_lvl_label.pack(pady=(10, 0))
        self.xp_label = ctk.CTkLabel(self.tab_quests, text="XP: 0 / 100", font=("Courier", 12), text_color="#AAAAAA")
        self.xp_label.pack(pady=0)
        self.xp_bar = ctk.CTkProgressBar(self.tab_quests, width=350, height=10, progress_color="#FFD700", fg_color="#1a1a1a")
        self.xp_bar.pack(pady=10)

        self.add_quest_frame = ctk.CTkFrame(self.tab_quests, fg_color="transparent")
        self.add_quest_frame.pack(pady=10)
        self.quest_entry = ctk.CTkEntry(self.add_quest_frame, placeholder_text="New Quest...", width=260, fg_color="#121212", border_color="#FFD700")
        self.quest_entry.grid(row=0, column=0, padx=5)
        ctk.CTkButton(self.add_quest_frame, text="ADD", width=60, fg_color="#332B00", text_color="#FFD700", hover_color="#554800", border_width=1, border_color="#FFD700", command=self.add_quest).grid(row=0, column=1, padx=5)

        self.quests_scroll = ctk.CTkScrollableFrame(self.tab_quests, width=380, height=450, fg_color="transparent")
        self.quests_scroll.pack(pady=10, fill="both", expand=True)

        # ==================== PROFILE (UPDATED) ====================
        try:
            avatar_path = os.path.join("assets", "avatar.webp")
            img = Image.open(avatar_path)
            self.avatar_img = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 140))
            self.avatar_label = ctk.CTkLabel(self.tab_profile, image=self.avatar_img, text="")
        except:
            self.avatar_label = ctk.CTkLabel(self.tab_profile, text="[ NO AVATAR ]", width=140, height=140, fg_color="#1a1a1a", text_color="#FF0000")
        self.avatar_label.pack(pady=(15, 5))

        self.class_label = ctk.CTkLabel(self.tab_profile, text="CLASS: DATA ENGINEER", font=("Courier", 20, "bold"), text_color="#00FF00")
        self.class_label.pack(pady=0)
        
        # НОВЫЙ БЛОК: РАНГ И СТРИКИ
        self.prof_rank_label = ctk.CTkLabel(self.tab_profile, text="RANK: Goldfish", font=("Courier", 18, "bold"), text_color="#FFD700")
        self.prof_rank_label.pack(pady=5)
        
        self.social_frame = ctk.CTkFrame(self.tab_profile, fg_color="transparent")
        self.social_frame.pack(pady=5)
        
        self.streak_label = ctk.CTkLabel(self.social_frame, text="🔥 STREAK: 0 DAYS", font=("Courier", 14, "bold"), text_color="#FF5555")
        self.streak_label.grid(row=0, column=0, padx=15)
        
        self.perc_label = ctk.CTkLabel(self.social_frame, text="🌍 TOP 50%", font=("Courier", 14, "bold"), text_color="#55AAFF")
        self.perc_label.grid(row=0, column=1, padx=15)

        # СТАТЫ
        self.stats_frame = ctk.CTkFrame(self.tab_profile, fg_color="#121212", corner_radius=10, border_width=1, border_color="#333333")
        self.stats_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.stat_cpp = ctk.CTkLabel(self.stats_frame, text="🧠 C++ Mastery: 10", font=("Courier", 14), text_color="#FFFFFF")
        self.stat_cpp.pack(anchor="w", padx=20, pady=(20, 10))
        self.stat_focus = ctk.CTkLabel(self.stats_frame, text="⚡ Deep Focus: 10", font=("Courier", 14), text_color="#FFFFFF")
        self.stat_focus.pack(anchor="w", padx=20, pady=10)
        self.stat_resist = ctk.CTkLabel(self.stats_frame, text="🛡️ Whse Resistance: 10", font=("Courier", 14), text_color="#FFFFFF")
        self.stat_resist.pack(anchor="w", padx=20, pady=10)

        # ==================== HISTORY ====================
        self.stats_label = ctk.CTkLabel(self.tab_hist, text="TODAY TOTAL: 0h 0m", font=("Courier", 18, "bold"), text_color="#00FF00")
        self.stats_label.pack(pady=10)
        self.hist_frame = ctk.CTkScrollableFrame(self.tab_hist, width=400, height=550, fg_color="transparent")
        self.hist_frame.pack(expand=True, fill="both")
        
        self.update_all_ui()

    # --- СИНХРОНИЗАЦИЯ UI ---
    def update_all_ui(self):
        self.update_quests_ui()
        self.update_profile_ui()
        self.update_history_ui()
        self.update_task_combo()

    def update_task_combo(self):
        self.cursor.execute("SELECT title FROM quests WHERE is_completed = 0 ORDER BY id DESC")
        quests = [row[0] for row in self.cursor.fetchall()]
        if not quests:
            quests = ["Select or type task..."]
            self.task_combo.set("Select or type task...")
        else:
            if self.task_combo.get() == "Select or type task..." or self.task_combo.get() == "":
                self.task_combo.set(quests[0])
        self.task_combo.configure(values=quests)

    def update_quests_ui(self):
        xp = self.get_xp()
        level = (xp // 100) + 1
        current_lvl_xp = xp % 100
        
        self.q_lvl_label.configure(text=f"LEVEL {level}")
        self.xp_label.configure(text=f"XP: {current_lvl_xp} / 100")
        self.xp_bar.set(current_lvl_xp / 100.0)

        for widget in self.quests_scroll.winfo_children(): widget.destroy()
        self.cursor.execute("SELECT id, title FROM quests WHERE is_completed = 0 ORDER BY id DESC")
        quests = self.cursor.fetchall()

        if not quests:
            ctk.CTkLabel(self.quests_scroll, text="All quests completed! Enjoy your rest.", text_color="gray").pack(pady=20)
            return

        for q_id, title in quests:
            frame = ctk.CTkFrame(self.quests_scroll, fg_color="#1a1a1a", corner_radius=5)
            frame.pack(fill="x", pady=5, padx=5)
            cb = ctk.CTkCheckBox(frame, text=title, font=("Courier", 14), text_color="#FFFFFF", hover_color="#FFD700", fg_color="#332B00", border_color="#FFD700", command=lambda qid=q_id: self.complete_quest(qid))
            cb.pack(side="left", padx=10, pady=10)

    def update_profile_ui(self):
        self.cursor.execute('SELECT xp, current_streak FROM user_stats WHERE id = 1')
        row = self.cursor.fetchone()
        xp = row[0]
        streak = row[1] if row[1] else 0
        
        rank_text = self.get_rank(xp)
        
        total_mins = self.get_today_stats() // 60
        perc_text = self.get_percentile(total_mins)

        self.prof_rank_label.configure(text=f"RANK: {rank_text}")
        self.streak_label.configure(text=f"🔥 STREAK: {streak} DAYS")
        self.perc_label.configure(text=f"🌍 {perc_text}")

        cpp_stat = 10 + int(xp * 0.15)
        focus_stat = 10 + int(xp * 0.10)
        resist_stat = 10 + int(xp * 0.25)

        self.stat_cpp.configure(text=f"🧠 C++ Mastery: {cpp_stat}")
        self.stat_focus.configure(text=f"⚡ Deep Focus: {focus_stat}")
        self.stat_resist.configure(text=f"🛡️ Whse Resistance: {resist_stat}")

    

    def add_quest(self):
        title = self.quest_entry.get()
        if title:
            self.cursor.execute("INSERT INTO quests (title) VALUES (?)", (title,))
            self.conn.commit()
            self.quest_entry.delete(0, "end")
            self.update_all_ui()

    def complete_quest(self, quest_id):
        self.cursor.execute("UPDATE quests SET is_completed = 1 WHERE id = ?", (quest_id,))
        self.add_xp(20)
        self.log(f"RPG: Quest completed! +20 XP")
        self.after(300, self.update_all_ui)
        play_reward_sound()

    def change_volume(self, value):
        self.current_volume = value
        if self.is_muted: self.toggle_mute()
        pygame.mixer.music.set_volume(self.current_volume)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0.0)
            self.mute_btn.configure(text="🔇 MUTED", text_color="#888888", border_color="#888888")
        else:
            pygame.mixer.music.set_volume(self.current_volume)
            self.mute_btn.configure(text="🔊 MUTE", text_color="#00FF00", border_color="#00FF00")

    def on_entry_change(self, event):
        val = self.manual_time_entry.get()
        if val.isdigit(): self.timer_display.configure(text=f"{val}:00")

    def add_time(self, mins):
        current = self.manual_time_entry.get()
        new_val = int(current) + mins if current.isdigit() else mins
        self.manual_time_entry.delete(0, "end")
        self.manual_time_entry.insert(0, str(new_val))
        self.timer_display.configure(text=f"{new_val}:00")

    def reset_time(self):
        self.manual_time_entry.delete(0, "end")
        self.manual_time_entry.insert(0, "0")
        self.timer_display.configure(text="0:00")

    def log(self, message):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{time_str}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def start_focus(self):
        try: duration_mins = int(self.manual_time_entry.get())
        except: return
        if duration_mins <= 0: return
        task = self.task_combo.get()
        if not task or task == "Select or type task...": return

        ctypes.windll.kernel32.SetThreadExecutionState(KEEP_AWAKE)
        self.is_running = True
        self.total_duration = duration_mins * 60
        self.seconds_left = self.total_duration
        self.total_session_time = 0
        
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.manual_time_entry.configure(state="disabled")
        self.task_combo.configure(state="disabled")

        assets_dir = "assets"
        if os.path.exists(assets_dir):
            tracks = [f for f in os.listdir(assets_dir) if f.endswith('.mp3') and f != "alarm.mp3"]
            if tracks:
                chosen_track = random.choice(tracks)
                pygame.mixer.music.load(os.path.join(assets_dir, chosen_track))
                pygame.mixer.music.set_volume(0.0 if self.is_muted else self.current_volume)
                pygame.mixer.music.play(loops=-1)
                self.log(f"AUDIO: Playing '{chosen_track}'")

        self.log(f"FLOW INITIATED. Target: {task}.")
        threading.Thread(target=self.clock_engine, daemon=True).start()

    def clock_engine(self):
        while self.is_running and self.seconds_left > 0:
            time.sleep(1)
            self.seconds_left -= 1
            self.total_session_time += 1
            
            h, r = divmod(self.seconds_left, 3600)
            m, s = divmod(r, 60)
            
            self.after(0, lambda: self.timer_display.configure(text=f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"))
            self.after(0, lambda: self.progress_bar.set(self.total_session_time / self.total_duration))
            
            if self.seconds_left <= 0: 
                self.is_running = False
                self.after(0, lambda: self.stop_focus(completed=True))

    def stop_focus(self, completed=False):
        self.is_running = False
        if completed:
            self.log("🏆 TARGET ACHIEVED!")
            alarm_path = os.path.join("assets", "alarm.mp3")
            if os.path.exists(alarm_path) and not self.is_muted:
                pygame.mixer.music.load(alarm_path)
                pygame.mixer.music.set_volume(self.current_volume)
                pygame.mixer.music.play()
            
            # Начисляем опыт И обновляем стрик
            self.add_xp(50)
            self.update_streak()
            self.log("RPG: Session completed! +50 XP")

        else:
            pygame.mixer.music.stop()

        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        duration = self.total_session_time
        task = self.task_combo.get()
        
        if duration > 5:
            self.cursor.execute('INSERT INTO sessions (date, duration, task_name) VALUES (?, ?, ?)', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, task))
            self.conn.commit()
            self.update_all_ui() 
            threading.Thread(target=self.send_tg_report, args=(duration, task), daemon=True).start()

        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.manual_time_entry.configure(state="normal")
        self.task_combo.configure(state="normal")

    def update_history_ui(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT SUM(duration) FROM sessions WHERE date LIKE ?", (today + '%',))
        res = self.cursor.fetchone()[0]
        total_sec = res if res else 0
        h, r = divmod(total_sec, 3600)
        m, _ = divmod(r, 60)
        self.stats_label.configure(text=f"TODAY TOTAL: {h}h {m}m")
        for widget in self.hist_frame.winfo_children(): widget.destroy()
        self.cursor.execute("SELECT date, duration, task_name FROM sessions ORDER BY id DESC LIMIT 50")
        rows = self.cursor.fetchall()
        if not rows: return
        for row in rows:
            date_str, duration, task = row
            sh, sr = divmod(duration, 3600)
            sm, ss = divmod(sr, 60)
            card = ctk.CTkFrame(self.hist_frame, fg_color="#121212", corner_radius=8, border_width=1, border_color="#333333")
            card.pack(pady=5, fill="x")
            ctk.CTkLabel(card, text=f"🎯 {task}", font=("Courier", 14, "bold"), text_color="#00FF00").pack(anchor="w", padx=10, pady=(10, 2))
            ctk.CTkLabel(card, text=f"⏱ {sh}h {sm}m {ss}s  |  📅 {date_str[:16]}", font=("Courier", 11), text_color="#888888").pack(anchor="w", padx=10, pady=(0, 10))

    def send_tg_report(self, duration, task_name):
        mins, secs = divmod(duration, 60)
        text = f"⚡️ <b>GOD MODE</b>\n\n🎯 {task_name}\n⏱ {mins}m {secs}s\n\n<i>«Grind now. Rest later.»</i>"
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
        except: pass
 # ==================== Sound of tasks completing ====================
pygame.mixer.init()

def play_reward_sound():
    """
    Воспроизводит звук вознаграждения (Level Up / Quest Complete)
    """
    try:
        # Загружаем файл (убедись, что имя совпадает с твоим файлом)
        reward_sound = pygame.mixer.Sound('levelup.mp3')
        
        # Можно даже немного убавить громкость (от 0.0 до 1.0), 
        # чтобы звук не бил по ушам
        reward_sound.set_volume(0.5) 
        
        # Запускаем звук! В pygame он по умолчанию играет в фоне (асинхронно)
        reward_sound.play()
        
    except Exception as e:
        print(f"[ SYSTEM ] Ошибка аудиомодуля: файл не найден. {e}")

# --- Имитация выполнения таски в твоей системе ---
print("\n[ FOCUS OS ] Сетевой квест Cisco выполнен! +100 XP")







if __name__ == "__main__":
    app = FocusOS()
    app.mainloop()


    