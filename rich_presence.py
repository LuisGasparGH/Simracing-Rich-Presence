from configparser import ConfigParser
from pypresence import Presence
import subprocess, time, threading, pystray, sys
import src.game_funcs as game_funcs
# GUI APIs
from tkinter import *
from PIL import Image
# Game APIs
from pyaccsharedmemory import accSharedMemory
from inc.pyRfactor2SharedMemory.sharedMemoryAPI import SimInfoAPI
from r3e_api import R3ESharedMemory

class SimRacingRichPresence:
    def checkProcess(self, applicationName):
        list = str(subprocess.check_output('tasklist')).replace(" ", "").lower()
        
        if applicationName in list:
            return True
        else:
            return False

    def closeGameAPI(self):
        match self.runningGame:
            case "ac2-win64-shipping.exe":
                self.sharedMem.close()
            case "lemansultimate.exe":
                self.sharedMem.close()
            case "rrre64.exe":
                self.sharedMem.close()
        print(f"[DEBUG] {self.runningGame} API closed")
        
    def buildTray(self):
        self.trayIcon = Image.open(game_funcs.build_path("src/assets/icons/icon.ico"))
        self.trayApp = pystray.Icon("Simracing Rich Presence", self.trayIcon, menu=pystray.Menu(
            pystray.MenuItem("Exit", self.closeTray)
        ))
        
        self.trayApp.run()

    def closeTray(self):
        self.trayApp.stop()
        self.exitApp = True
        
    def createRPC(self):
        self.rpc = Presence(self.discordConfig['APPLICATION'][self.runningGame])
        self.rpc.connect()
        print(f"[DEBUG] Discord RPC connected")
        self.discordConnected = True
    
    def updateRPC(self):
        self.rpc.update(state=self.latestData["state"],
                        details=self.latestData["details"],
                        end=self.latestData["end"],
                        large_image=self.latestData["large_image"],
                        large_text=self.latestData["large_text"],
                        small_image=self.latestData["small_image"],
                        small_text=self.latestData["small_text"])
        
    def closeRPC(self):
        self.rpc.clear()
        self.rpc.close()
        print(f"[DEBUG] Discord RPC closed")
        self.discordConnected = False

    def __init__(self):
        self.exitApp = False
        self.trayIconThread = threading.Thread(target=self.buildTray, args=())
        self.trayIconThread.start()
        print("[DEBUG] Tray icon launched")

        self.discordConfig = ConfigParser()
        self.discordConfig.read(game_funcs.build_path('src/assets/configs/discord_config.ini'))

        self.discordRunning = False
        self.discordConnected = False
        self.runningGame = None
        self.gameConfig = ConfigParser()
        self.latestData = {}

        while not self.exitApp:
            self.discordRunning = self.checkProcess("discord.exe")
            print(f"[DEBUG] Discord running: {self.discordRunning}")

            if self.discordRunning:
                for game in self.discordConfig['APPLICATION']:
                    if self.checkProcess(game):
                        self.runningGame = game
                        print(f"[DEBUG] {game} running")
                        self.gameConfig.read(game_funcs.build_path(f'src/assets/configs/{game.lower().replace(".exe", "")}_config.ini'))
                        match self.runningGame:
                            case "ac2-win64-shipping.exe":
                                self.sharedMem = accSharedMemory()
                                break
                            case "lemansultimate.exe":
                                self.sharedMem = SimInfoAPI()
                                break
                            case "rrre64.exe":
                                self.sharedMem = R3ESharedMemory()
                                break
                        print(f"[DEBUG] {self.runningGame} API connected")
                
                while self.runningGame != None:
                    if not self.discordConnected:
                        self.createRPC()
                    
                    match self.runningGame:
                        case "ac2-win64-shipping.exe":
                            self.latestData = game_funcs.getAccTelemetry(self.sharedMem, self.gameConfig)
                        case "lemansultimate.exe":
                            self.latestData = game_funcs.getLmuTelemetry(self.sharedMem, self.gameConfig)
                        case "rrre64.exe":
                            self.latestData = game_funcs.getR3eTelemetry(self.sharedMem, self.gameConfig)

                    print(f"[DEBUG] {self.latestData}")
                    self.updateRPC()

                    if self.exitApp:
                        break

                    if not self.checkProcess(self.runningGame):
                        print(f"[DEBUG] {self.runningGame} closed")
                        self.closeGameAPI()
                        self.runningGame = None
                        self.closeRPC()
                    
                    time.sleep(1)
            
            time.sleep(1)
        
        print("Exiting Simracing Rich Presence")
        self.closeGameAPI()
        self.closeRPC()
        print("Quitting application")
        sys.exit()

# try:
simracingRP = SimRacingRichPresence()
# except:
#     pass