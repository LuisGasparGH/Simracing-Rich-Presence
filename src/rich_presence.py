import irsdk
import pyaccsharedmemory
import r3e_api
# add rfactor 2 api after
from pypresence import Presence
from tkinter import *
from configparser import ConfigParser
from PIL import Image
import math, time, os, threading, sys, pystray
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
class ACC_API: #DONE, TO TEST
    def read_acc_telemetry(self):
        telemetry = self.shared_mem.read_shared_memory()

        if telemetry != None:
            match telemetry.Graphics.status:
                case pyaccsharedmemory.ACC_STATUS.ACC_OFF:
                    self.latest_telemetry["state"] = "In menus"
                    self.latest_telemetry["details"] = None
                    self.latest_telemetry["end"] = None
                    self.latest_telemetry["large_image"] = "acc_logo"
                    self.latest_telemetry["large_text"] = None
                    self.latest_telemetry["small_image"] = None
                    self.latest_telemetry["small_text"] = None
                case pyaccsharedmemory.ACC_STATUS.ACC_REPLAY:
                    car = self.config['CARS'][telemetry.Static.car_model.replace("\x00", "").lower()]
                    brand = car.split(" ")[0].lower()
                    track = self.config['TRACKS'][telemetry.Static.track.replace("\x00", "").lower()]

                    self.latest_telemetry["state"] = f"{car} at {track}"
                    self.latest_telemetry["details"] = f"Watching a {telemetry.Graphics.session_type} replay"
                    self.latest_telemetry["end"] = None
                    self.latest_telemetry["large_image"] = track.lower()
                    self.latest_telemetry["large_text"] = track
                    self.latest_telemetry["small_image"] = brand.lower()
                    self.latest_telemetry["small_text"] = car
                case pyaccsharedmemory.ACC_STATUS.ACC_LIVE | pyaccsharedmemory.ACC_STATUS.ACC_PAUSE:
                    car = self.config['CARS'][telemetry.Static.car_model.replace("\x00", "").lower()]
                    brand = car.split(" ")[0].lower()
                    track = self.config['TRACKS'][telemetry.Static.track.replace("\x00", "").lower()]

                    self.latest_telemetry["state"] = f"{car} at {track}"
                    pb_split = telemetry.Graphics.best_time_str.replace("\x00", "").split(":")
                    if pb_split[0] is "35791":
                        personal_best = None
                    else:
                        personal_best = f"{pb_split[0]}:{pb_split[1]}.{pb_split[2]}"
                    
                    match telemetry.Graphics.session_type:
                        case pyaccsharedmemory.ACC_SESSION_TYPE.ACC_PRACTICE | \
                                pyaccsharedmemory.ACC_SESSION_TYPE.ACC_HOTLAP | \
                                pyaccsharedmemory.ACC_SESSION_TYPE.ACC_HOTLAPSUPERPOLE | \
                                pyaccsharedmemory.ACC_SESSION_TYPE.ACC_HOTSTINT:
                            self.latest_telemetry["details"] = f"{telemetry.Graphics.session_type} | PB: {personal_best}"
                        case pyaccsharedmemory.ACC_SESSION_TYPE.ACC_QUALIFY | \
                                pyaccsharedmemory.ACC_SESSION_TYPE.ACC_RACE:
                            self.latest_telemetry["details"] = f"{telemetry.Graphics.session_type} | P{telemetry.Graphics.position} of {telemetry.Static.num_cars}"
                    
                    if telemetry.Graphics.session_time_left > 0.0:
                        self.latest_telemetry["end"] = math.ceil(time.time() + (telemetry.Graphics.session_time_left/1000))
                    else:
                        self.latest_telemetry["end"] = None
                    
                    self.latest_telemetry["large_image"] = track.lower()
                    self.latest_telemetry["large_text"] = track
                    self.latest_telemetry["small_image"] = brand.lower()
                    self.latest_telemetry["small_text"] = car

            shared_variables["AC2-Win64-Shipping.exe"]["latest_data"] = self.latest_telemetry

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(get_path('assets/configs/acc_config.ini'))
        
        self.shared_mem = pyaccsharedmemory.accSharedMemory()
        self.latest_telemetry = {}

        while True:
            check_process_status("AC2-Win64-Shipping.exe")

            if shared_variables["Discord.exe"]["connected"] and shared_variables["AC2-Win64-Shipping.exe"]["running"]:
                self.read_acc_telemetry()
            time.sleep(1)
#=============================================================================================================================
class R3E_API:
    def read_r3e_telemetry(self):
        telemetry = self.shared_mem.update_buffer()

        # https://github.com/Yuvix25/r3e-python-api/blob/main/r3e_api/data/data.cs

        if telemetry != None:
            if self.shared_mem.get_value('Shared.GameInMenus'):
                self.latest_telemetry["state"] = "In menus"
                self.latest_telemetry["details"] = None
                self.latest_telemetry["end"] = None
                self.latest_telemetry["large_image"] = "r3e_logo"
                self.latest_telemetry["large_text"] = None
                self.latest_telemetry["small_image"] = None
                self.latest_telemetry["small_text"] = None
            elif self.shared_mem.get_value('Shared.GameInReplay'):
                car = self.config['CARS'][self.shared_mem.get_value('DriverInfo.ModelId')]
            elif self.shared_mem.get_value('Shared.GameInPause') or self.shared_mem.get_value('Shared.GameUnused1'):
                pass
            
            shared_variables["RRRE64.exe"]["latest_data"] = self.latest_telemetry

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(get_path('assets/configs/r3e_config.ini'))

        self.shared_mem = r3e_api.R3ESharedMemory()
        self.shared_mem.update_offsets()
        self.latest_telemetry = {}

        while True:
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

    def create_and_connect_api(self, simulator):
        self.rich_presence = Presence(self.config['APPLICATION'][simulator])
        try:
            self.rich_presence.connect()
            shared_variables["Discord.exe"]["connected"] = True
        except:
            pass

    def update_rich_presence(self, simulator):
        try:
            self.rich_presence.update(state=shared_variables[simulator]["latest_data"]["state"],
                                    details=shared_variables[simulator]["latest_data"]["details"],
                                    end=shared_variables[simulator]["latest_data"]["end"],
                                    large_image=shared_variables[simulator]["latest_data"]["large_image"],
                                    large_text=shared_variables[simulator]["latest_data"]["large_text"],
                                    small_image=shared_variables[simulator]["latest_data"]["small_image"],
                                    small_text=shared_variables[simulator]["latest_data"]["small_text"])
        except:
            pass

    def __init__(self):
        self.config = ConfigParser()
        self.config.read(get_path('assets/configs/discord_config.ini'))

        while True:
            if shared_variables["exit"]:
                self.close_discord_api()
                break
            check_process_status("Discord.exe")
                
            if shared_variables["Discord.exe"]["running"]:
                for simulator in shared_variables:
                    if simulator is not "exit" and shared_variables[simulator]["running"]:
                        self.create_and_connect_api(simulator)
                        while shared_variables[simulator]["running"]:
                            self.update_rich_presence(simulator)
                            time.sleep(1)
                        self.close_discord_api()
            time.sleep(1)
#=============================================================================================================================
class Tkinter_APP:
    def close_tray_app(self):
        self.tray_app.stop()
        shared_variables['exit'] = True

    def tray_func(self):
        self.tray_icon = Image.open(get_path("assets/simracing_rp_icon.ico"))
        self.tray_app = pystray.Icon("Simracing Rich Presence", self.tray_icon, menu=pystray.Menu(
            pystray.MenuItem("iRacing Connected", None),
            pystray.MenuItem("ACC Connected", None),
            pystray.MenuItem("Raceroom Connected", None),
            pystray.MenuItem("Exit", self.close_tray_app)
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
    gui_class = Tkinter_APP()
except: 
    pass