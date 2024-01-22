import irsdk
import pyaccsharedmemory
import r3e_api
# add rfactor 2 api after
from pypresence import Presence
from tkinter import *
from urllib.request import urlretrieve
from configparser import ConfigParser
from datetime import date
from PIL import Image, ImageTk
import math, time, os, threading, sys, requests, pystray, pycountry
#=============================================================================================================================
shared_variables = {
    "exit": False,
    "iRacingSim64DX11.exe": {
        "running": False,
        "connected": False,
        "latest_data": {}
    },
    "AC2-Win64-Shipping.exe": {
        "running": False,
        "latest_data": {}
    },
    "RRRE64.exe": {
        "running": False,
        "latest_data": {}
    },
    "Discord.exe": {
        "running": False,
        "connected": False,
    }
}
#=============================================================================================================================
def get_path(relative):
    try: 
        base_path = sys._MEIPASS
    except Exception: 
        base_path = os.path.abspath('.')
    
    return os.path.join(base_path, relative)
#=============================================================================================================================
def check_process_status(simulator):
    try:
        list = os.popen('wmic process get description').read()
    except:
        pass

    if simulator in list and not shared_variables[simulator]["running"]:
        shared_variables[simulator]["running"] = True
    elif simulator not in list and shared_variables[simulator]["running"]:
        shared_variables[simulator]["running"] = False
#=============================================================================================================================
class iRacing_API:
    def close_iracing_api(self):
        #TODO - figure out how IRSDK connection is gracefully closed
        pass

    def read_iracing_telemetry(self):
        pass

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(get_path('assets/configs/iracing_config.ini'))

        while True:
            if shared_variables["exit"]:
                self.close_iracing_api()
            check_process_status("iRacingSim64DX11.exe")

            if shared_variables["Discord.exe"]["connected"] and shared_variables["iRacingSim64DX11.exe"]["running"]:
                self.read_iracing_telemetry()
            time.sleep(1)
#=============================================================================================================================
class ACC_API:
#=============================================================================================================================
    def close_acc_api(self):
        #TODO - figure out how ACC API connection is gracefully closed
        pass
#=============================================================================================================================
    def read_acc_telemetry(self):
        telemetry = accSharedMemory().read_shared_memory()

        if telemetry != None:
            self.status = telemetry.Graphics.status

            if self.status != ACC_STATUS.ACC_OFF:
                self.car_model = telemetry.Static.car_model.replace("\x00", "").lower()
                self.track = telemetry.Static.track.replace("\x00", "").lower()
                self.session_type = telemetry.Graphics.session_type

                if self.status != ACC_STATUS.ACC_REPLAY:
                    self.best_time_str = telemetry.Graphics.best_time_str.replace("\x00", "")
                    if self.best_time_str == "35791:23:647": 
                        self.best_time_str = "None"
                    else:
                        split_str = self.best_time_str.split(":")
                        self.best_time_str = split_str[0] + ":" + split_str[1] + "." + split_str[2]

                    self.position = telemetry.Graphics.position
                    self.num_cars = telemetry.Static.num_cars
                    
                    self.is_online = telemetry.Static.is_online
                    self.session_time_left = telemetry.Graphics.session_time_left/1000

                    if self.session_time_left > 0.0:
                        self.session_end = math.ceil(time.time() + self.session_time_left)
                        self.timed_session = True
                    else:
                        self.session_end = None
                        self.timed_session = False
        else: 
            self.status = ACC_STATUS.ACC_OFF
#=============================================================================================================================
    def __init__(self):
        self.config = ConfigParser()
        self.config.read(self.get_path('assets/config.ini'))

        self.acc_running = False
        self.status = ACC_STATUS.ACC_OFF
        self.timed_session = False

        self.lfm_series_list = []
        self.lfm_checked = False
        self.lfm_data = {"series": None, "split": None, "sof": None}

        while True:
            if self.exit == True: 
                sys.exit()
            self.check_process_status()

            if len(self.lfm_series_list) == 0 or self.lfm_series_list[0]['search_date'] != date.today():
                self.lfm_series_fetch()

            if self.acc_running == True and self.discord_connected == True:        
                self.read_acc_telemetry()
                self.update_rich_presence()
            time.sleep(1)
#=============================================================================================================================
class R3E_API:
    def close_r3e_api(self):
        #TODO - figure out how R3E API connection is gracefully closed
        pass
#=============================================================================================================================
    def read_r3e_telemetry(self):
        pass

    def __init__(self):
        self.config.read(get_path('assets/configs/r3e_config.ini'))

        while True:
            if shared_variables["exit"]:
                self.close_r3e_api()
            check_process_status("RRRE64.exe")

            if shared_variables["Discord.exe"]["connected"] and shared_variables["RRRE64.exe"]["running"]:
                self.read_r3e_telemetry()
            time.sleep(1)
#=============================================================================================================================
class Discord_API:
    def close_discord_api(self):
        try:
            self.rich_presence.clear()
            self.rich_presence.close()
        except:
            pass

    def update_rich_presence(self):
        match self.status:
            case ACC_STATUS.ACC_OFF:
                self.in_game = False
                self.lfm_checked = False
                self.lfm_data = {"series": None, "split": None, "sof": None}
                
                self.state = "In menus"
                self.details = None
                self.end = None
                self.large_image = "acc_logo"
                self.large_text = None
                self.small_image = None
                self.small_text = None
            case ACC_STATUS.ACC_REPLAY:
                self.in_game = False
                car_mapped = self.config['CARS'][self.car_model]
                car_brand = car_mapped.split(" ")[0].lower()
                track_mapped = self.config['TRACKS'][self.track]
                
                self.state = f"{car_mapped} at {track_mapped}" 
                self.details = f"Watching a {self.session_type} Replay"
                self.end = None
                self.large_image = self.track.lower()
                self.large_text = track_mapped
                self.small_image = car_brand.lower()
                self.small_text = car_mapped
            case ACC_STATUS.ACC_LIVE | ACC_STATUS.ACC_PAUSE:
                self.in_game = True
                car_mapped = self.config['CARS'][self.car_model].split("/")[0]
                class_mapped = self.config['CARS'][self.car_model].split("/")[1].upper()
                car_brand = car_mapped.split(" ")[0].lower()
                track_mapped = self.config['TRACKS'][self.track]
                
                if self.is_online == True and self.lfm_checked == False:
                    for lfm_series in self.lfm_series_list:
                        if class_mapped in lfm_series['classes'] and self.track == lfm_series['active_track']:
                            self.lfm_next_race_info(series=lfm_series)
                    self.lfm_checked = True

                match self.is_online:
                    case True: 
                        self.is_online = "Online"
                    case False: 
                        self.is_online = "Offline"

                if self.lfm_data['split'] != None:
                    self.state = f"Split {self.lfm_data['split']} | SoF: {self.lfm_data['sof']} | {self.lfm_data['series']}"
                    self.details = "LFM"
                else:
                    self.state = f"{car_mapped} at {track_mapped}"
                    self.details = str(self.is_online)
                
                self.details += f" {self.session_type}"
                self.end = self.session_end
                self.large_image = self.track.lower()
                self.large_text = track_mapped
                self.small_image = car_brand.lower()
                self.small_text = car_mapped
        if self.in_game:
            match self.session_type:
                case ACC_SESSION_TYPE.ACC_PRACTICE | ACC_SESSION_TYPE.ACC_HOTLAP | ACC_SESSION_TYPE.ACC_HOTLAPSUPERPOLE | ACC_SESSION_TYPE.ACC_HOTSTINT:
                    self.details += f" | PB: {self.best_time_str}"
                    if self.timed_session == False: self.end = None
                case ACC_SESSION_TYPE.ACC_QUALIFY | ACC_SESSION_TYPE.ACC_RACE:
                    self.details += f" | P{self.position} of {self.num_cars}"

        try: self.rich_presence.update(state = self.state, details = self.details, end = self.end, large_image = self.large_image,
                                       large_text = self.large_text, small_image = self.small_image, small_text = self.small_text)
        except: 
            pass

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(get_path('assets/configs/discord_config.ini'))

        self.rich_presence = Presence(self.config['USER']['RichPresenceID'])

        while True:
            if shared_variables["exit"]:
                self.close_discord_api()
                break

            check_process_status("Discord.exe")

            if shared_variables["Discord.exe"]["running"] and not shared_variables["Discord.exe"]["connected"]:
                try:
                    self.rich_presence.connect()
                    shared_variables["Discord.exe"]["connected"] = True
                except:
                    time.sleep(1)
                
            if shared_variables["Discord.exe"]["connected"]:
                if shared_variables["iRacingSim64DX11.exe"]["running"] or shared_variables["AC2-Win64-Shipping.exe"]["running"] or shared_variables["RRRE64.exe"]["running"]:
                    self.update_rich_presence()

#=============================================================================================================================
class Tkinter_GUI:
    def close_gui(self):
        if self.window_active:
            self.window.quit()
        
        self.tray_app.stop()
        shared_variables['exit'] = True
# #=============================================================================================================================
#     def clear_window(self):
#         for widget in self.window_active_widgets:
#             widget.place_forget()
        
#         self.window_active_widgets.clear()
# #=============================================================================================================================
#     def generate_window_elements(self):
#         self.top_label = Label(self.window, width=26, font=("Franklin Gothic", 12, "bold"))
#         self.top_label.place(x=0, y=5)
#         self.info_label = Label(self.window, width=32, height=2, wraplength=200, font=("Franklin Gothic", 10))
#         self.id_string = StringVar()
#         self.id_entry = Entry(self.window, textvariable=self.id_string, width=15, font=("Franklin Gothic", 12, "bold"))
#         self.search_button = Button(self.window, command=self.lfm_user_search, width=13, font=("Franklin Gothic", 12, "bold"))
#         self.driver_name = Label(self.window, width=18, anchor="w", font=("Franklin Gothic", 10))
#         self.driver_country = Label(self.window, width=18, anchor="w", font=("Franklin Gothic", 10))
#         self.driver_elo = Label(self.window, width=18, anchor="w", font=("Franklin Gothic", 10))
#         self.driver_avatar = Label(self.window, width=60, height=60, bd=1, relief="solid")
#         self.confirm_button = Button(self.window, command=self.lfm_user_set, font=("Franklin Gothic", 12, "bold"))
#         self.cancel_button = Button(self.window, command=self.window_draw_search, font=("Franklin Gothic", 12, "bold"))
#         self.change_button = Button(self.window, command=self.window_draw_search, font=("Franklin Gothic", 12, "bold"))
# #=============================================================================================================================
#     def window_draw_search(self):
#         self.clear_window()
#         self.lfm_update = False

#         self.top_label.config(text="Insert your LFM ID")
#         self.info_label.config(text="You can find your ID in the URL of your profile page")
#         self.info_label.place(x=0, y=30)
#         self.id_entry.place(x=65, y=75)
#         self.search_button.config(text="Search User")
#         self.search_button.place(x=63, y=105)
        
#         self.window_active_widgets.extend([self.info_label, self.id_entry, self.search_button])
# #=============================================================================================================================
#     def window_draw_user(self, version):
#         self.clear_window()

#         if version == 3:
#             self.lfm_update = True
#             self.lfm_user_search()

#         self.driver_name.config(text=f"Driver: {self.lfm_name}")
#         self.driver_name.place(x=15, y=35)
#         self.driver_country.config(text=f"Country: {self.lfm_country}")
#         self.driver_country.place(x=15, y=55)
#         self.driver_elo.config(text=f"ELO Rating: {self.lfm_rating}")
#         self.driver_elo.place(x=15, y=75)
#         self.driver_avatar.config(image=self.lfm_avatar, bd=1, relief="solid")
#         self.driver_avatar.place(x=180, y=34)
        
#         self.window_active_widgets.extend([self.driver_name, self.driver_country, self.driver_elo, self.driver_avatar])
        
#         if version == 2:
#             self.top_label.config(text="LFM Driver Found")
#             self.confirm_button.config(text="Confirm")
#             self.confirm_button.place(x=30, y=105)
#             self.cancel_button.config(text="Cancel")
#             self.cancel_button.place(x=160, y=105)
            
#             self.window_active_widgets.extend([self.confirm_button, self.cancel_button])
#         elif version == 3:
#             self.top_label.config(text="LFM Driver Selected")
#             self.change_button.config(text="Change User")
#             self.change_button.place(x=75, y=105)
#             self.window_active_widgets.extend([self.change_button])
# #=============================================================================================================================
#     def lfm_user_search(self):
#         if self.lfm_update == False:
#             endpoint_id = self.id_string.get()
#         else:
#             endpoint_id = self.config['USER']['LFMID']
        
#         lfm_user = requests.get(f"{self.config['ENDPOINTS']['UserSearch']}{endpoint_id}").json()

#         if "id" in lfm_user:
#             self.lfm_id = lfm_user['id']
#             self.lfm_name = f"{lfm_user['vorname']} {lfm_user['nachname']}"
#             self.lfm_country = pycountry.countries.get(alpha_2=lfm_user['origin'].split("-")[0]).name
#             self.lfm_rating = lfm_user['rating_by_sim'][0]['rating']
            
#             urlretrieve(lfm_user['avatar'], self.get_path('assets/lfm_avatar.png'))
#             self.lfm_avatar = ImageTk.PhotoImage(master=self.window, image=Image.open(self.get_path('assets/lfm_avatar.png')).resize((60,60)))
            
#             if self.lfm_update == 0:
#                 self.window_draw_user(version=2)
#         else:
#             self.search_button.config(text="User Not Found")
# #=============================================================================================================================
#     def lfm_user_set(self):
#         self.config['USER']['LFMID'] = str(self.lfm_id)
        
#         with open(self.get_path('assets/config.ini'), 'w') as config:
#             self.config.write(config)
        
#         self.window_draw_user(version=3)
# #=============================================================================================================================
#     def lfm_series_fetch(self):
#         self.lfm_series_list.append({"search_date": date.today()})
#         series_info = requests.get(self.config['ENDPOINTS']['GetSeries']).json()
        
#         for series in series_info['series'][0]['series']:
#             entry = {"name": series['series_name'], "id": int(series['event_id']),
#                      "classes": series['settings']['championship_settings']['car_classes'][0]['class'],
#                      "track": series['active_track']['track_name'], "team_series": bool(series['team_event'])}
            
#             self.lfm_series_list.append(entry)
# #=============================================================================================================================
#     def lfm_integration_window(self):
#         if self.window_active == False:
#             self.window_active = True
#             self.window = Tk()
#             self.window.iconphoto(False, ImageTk.PhotoImage(image=Image.open(self.get_path("assets/lfm_icon.ico"))))
#             self.window.title("LFM Integration")
#             self.window.geometry("260x150")
#             self.generate_window_elements()
#             self.window.resizable(width=False,height=False)
#             self.window_active_widgets = []

#             if int(self.config['USER']['LFMID']) == 0:
#                 self.window_draw_search()
#             else:
#                 self.window_draw_user(version=3)
            
#             self.window.mainloop()
#             self.window.quit()
#             self.window_active = False
# #=============================================================================================================================
#     def lfm_next_race_info(self, series):
#         latest_races = requests.get(f"{self.config['ENDPOINTS']['RecentRaces']}{series['id']}").json()
#         next_race_id = int(latest_races['data'][0]['race_id'])+1
#         next_race_info = requests.get(f"{self.config['ENDPOINTS']['RaceInfo']}{next_race_id}").json()

#         if next_race_info['session_running'] == 1 and next_race_info['splits']['driver_count'] > 0:
#             for split in next_race_info['splits']['participants']:
#                 if series['team_series'] == False:
#                     for driver in split['entries']:
#                         if int(driver['user_id']) == int(self.config['USER']['LFMID']):
#                             self.lfm_data['series'] = int(next_race_info['event']['event_name'])
#                             self.lfm_data['split'] = int(driver['split'])
#                             if self.lfm_data['split'] == 1:
#                                 self.lfm_data['sof'] = next_race_info['sof']
#                             elif self.lfm_data['split'] > 1:
#                                 self.lfm_data['sof'] = next_race_info[f"split{self.lfm_data['split']}_sof"]
#                 else:
#                     for team in split['entries']:
#                         for driver in team['drivers']:
#                             if int(driver['user_id']) == int(self.config['USER']['LFMID']):
#                                 self.lfm_data['series'] = int(next_race_info['event']['event_name'])
#                                 self.lfm_data['split'] = int(driver['split'])
#                                 if self.lfm_data['split'] == 1:
#                                     self.lfm_data['sof'] = next_race_info['sof']
#                                 elif self.lfm_data['split'] > 1:
#                                     self.lfm_data['sof'] = next_race_info[f"split{self.lfm_data['split']}_sof"]
#=============================================================================================================================
    def tray_func(self):
        self.tray_icon = Image.open(get_path("assets/simracing_rp_icon.ico"))
        self.tray_app = pystray.Icon("Simracing Rich Presence", self.tray_icon, menu=pystray.Menu(
            pystray.MenuItem("iRacing Connected", None),
            pystray.MenuItem("ACC Connected", None),
            pystray.MenuItem("Raceroom Connected", None),
            pystray.MenuItem("Exit", self.close_gui)
        ))
        
        self.tray_app.run()

    def __init__(self):
        self.window_active = False
        self.tray_thread = threading.Thread(target=self.tray_func, args=())
        self.tray_thread.start()
    
        while True:
            if shared_variables["exit"] and not shared_variables["iRacingSim64DX11.exe"]["connected"] and not shared_variables["Discord.exe"]["connected"]:
                sys.exit()
            time.sleep(1)
#=============================================================================================================================
try: 
    iracing_class = iRacing_API()
    acc_class = ACC_API()
    r3e_class = R3E_API()
    discord_class = Discord_API()
    gui_class = Tkinter_GUI()
except: 
    pass