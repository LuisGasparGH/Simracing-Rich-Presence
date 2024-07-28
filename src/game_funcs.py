import sys, os, time, math
import unicodedata
from datetime import timedelta
from pyaccsharedmemory import ACC_SESSION_TYPE, ACC_STATUS
from inc.pypcars2api.pypcars2api import definitions as AMS2_DEFINITION

removeChars = ["#", "'", "(", ")"]

def build_path(relative):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative)

def textNormalizer(text):
    normalizedText = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').lower().replace(" ", "_")
    
    for char in removeChars:
        normalizedText = normalizedText.replace(char, "")
    
    return normalizedText
    

def getAccTelemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.read_shared_memory()

    if telemetry != None:
        if telemetry.Graphics.status == ACC_STATUS.ACC_OFF:
            latestData["state"] = "In menus"
            latestData["details"] = None
            latestData["end"] = None
            latestData["large_image"] = "acc_logo"
            latestData["large_text"] = None
            latestData["small_image"] = None
            latestData["small_text"] = None
        else:
            # TODO - swap this to decode
            car = config['CARS'][telemetry.Static.car_model.replace("\x00", "").lower()]
            brand = car.split(" ")[0].lower()
            track = config['TRACKS'][telemetry.Static.track.replace("\x00", "").lower()]

            latestData["state"] = f"{car} at {track}"

            match telemetry.Graphics.status:
                case ACC_STATUS.ACC_REPLAY:      
                    latestData["details"] = f"Watching a {telemetry.Graphics.session_type} replay"
                    latestData["end"] = None
                case ACC_STATUS.ACC_LIVE | ACC_STATUS.ACC_PAUSE:
                    if telemetry.Static.is_online:
                        onOff = "Online"
                    else:
                        onOff = "Offline"
                    
                    match telemetry.Graphics.session_type:
                        case ACC_SESSION_TYPE.ACC_PRACTICE | ACC_SESSION_TYPE.ACC_HOTLAP | \
                        ACC_SESSION_TYPE.ACC_HOTLAPSUPERPOLE | ACC_SESSION_TYPE.ACC_HOTSTINT:
                            pbSplit = telemetry.Graphics.best_time_str.replace("\x00", "").split(":")
                            if pbSplit[0] == "35791":
                                personalBest = None
                            else:
                                personalBest = f"{pbSplit[0]}:{pbSplit[1]}.{pbSplit[2]}"
                            latestData["details"] = f"{onOff} {telemetry.Graphics.session_type} | PB: {personalBest}"
                        case ACC_SESSION_TYPE.ACC_QUALIFY | ACC_SESSION_TYPE.ACC_RACE:
                            latestData["details"] = f"{onOff} {telemetry.Graphics.session_type} | P{telemetry.Graphics.position} of {telemetry.Static.num_cars}"
                    
                    # TODO - idenfity all edge case scenarios with the end time always increasing (because it is still loading or paused)
                    if telemetry.Graphics.session_time_left > 0.0:
                        latestData["end"] = math.ceil(time.time() + (telemetry.Graphics.session_time_left/1000))
                    else:
                        latestData["end"] = None
                    
            latestData["large_image"] = track.lower()
            latestData["large_text"] = track
            latestData["small_image"] = brand.lower()
            latestData["small_text"] = car

    return latestData

def getAms2Telemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.snapshot()

    if telemetry != None:
        if telemetry.mGameState == AMS2_DEFINITION.GAME_FRONT_END:
            latestData["state"] = "In menus"
            latestData["details"] = None
            latestData["end"] = None
            latestData["large_image"] = "ams2_logo"
            latestData["large_text"] = None
            latestData["small_image"] = None
            latestData["small_text"] = None
        else:
            car = telemetry.mCarName
            brand = car.split(" ")[0].lower()
            track = telemetry.mTrackLocation
            layout = telemetry.mTrackVariation

            latestData["state"] = f"{car} at {track} ({layout})"

            match telemetry.mSessionState:
                case AMS2_DEFINITION.GAME_FRONT_END_REPLAY | AMS2_DEFINITION.GAME_INGAME_REPLAY:
                    latestData["details"] = f"Watching a {telemetry.mSessionType} replay"
                    latestData["end"] = None
            

def getLmuTelemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.isSharedMemoryAvailable()
    
    if telemetry != None:
        sessionType = sharedMemAPI.Rf2Scor.mScoringInfo.mSession
        if sessionType == 0 or sharedMemAPI.isTrackLoaded() == 0:
            latestData["state"] = "In menus"
            latestData["details"] = None
            latestData["end"] = None
            latestData["large_image"] = "lmu_logo"
            latestData["large_text"] = None
            latestData["small_image"] = None
            latestData["small_text"] = None
        else:
            parsedCar = ""
            while parsedCar == "":
                parsedCar = textNormalizer(sharedMemAPI.playersVehicleScoring().mVehicleName.decode("utf-8"))
            car = config['CARS'][parsedCar]
            brand = car.split(" ")[0].lower()
            track = config['TRACKS'][textNormalizer(sharedMemAPI.Rf2Scor.mScoringInfo.mTrackName.decode("utf-8"))]
            
            latestData["state"] = f"{car} at {track}"
            
            if sharedMemAPI.Rf2Scor.mScoringInfo.mServerPublicIP != 0:
                onOff = "Online"
            else:
                onOff = "Offline"

            match sessionType:
                case 1 | 2 | 3 | 4:
                    personalBest = sharedMemAPI.playersVehicleScoring().mBestLapTime
                    if personalBest < 0:
                        personalBest = None
                    else:
                        pbSplit = str(timedelta(seconds=personalBest))[:-3].split(":")
                        personalBest = f"{pbSplit[1]}:{pbSplit[2]}"
                    latestData["details"] = f"{onOff} Practice | PB: {personalBest}"
                case 5 | 6 | 7 | 8 | 10 | 11 | 12 | 13:
                    if sessionType < 9:
                        session = "Qualifying"
                    else:
                        session = "Race"
                    classPlayer = sharedMemAPI.playersVehicleScoring().mVehicleClass
                    classPos = 1
                    classCars = 0
                    for index in range(sharedMemAPI.Rf2Scor.mScoringInfo.mNumVehicles):
                        if sharedMemAPI.Rf2Scor.mVehicles[index].mVehicleClass == classPlayer:
                            classCars += 1
                            if sharedMemAPI.Rf2Scor.mVehicles[index].mPlace < sharedMemAPI.playersVehicleScoring().mPlace:
                                classPos += 1
                    latestData["details"] = f"{onOff} {session} | P{classPos} of {classCars}"

            # TODO - idenfity all edge case scenarios with the end time always increasing (because it is still loading or paused)
            if sharedMemAPI.Rf2Scor.mScoringInfo.mEndET > 0.0:
                remaining_time = sharedMemAPI.Rf2Scor.mScoringInfo.mEndET - sharedMemAPI.Rf2Scor.mScoringInfo.mCurrentET
                latestData["end"] = math.ceil(time.time() + remaining_time)
            else:
                latestData["end"] = None
            
            latestData["large_image"] = track.lower()
            latestData["large_text"] = track
            latestData["small_image"] = brand.lower()
            latestData["small_text"] = car

    return latestData

def getR3eTelemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.update_buffer()

    if telemetry != None:
        if sharedMemAPI.get_value('SessionType') < 0:
            latestData["state"] = "In menus"
            latestData["details"] = None
            latestData["end"] = None
            latestData["large_image"] = "r3e_logo"
            latestData["large_text"] = None
            latestData["small_image"] = None
            latestData["small_text"] = None
        else:
            car = sharedMemAPI.get_value('VehicleInfo.Name')
            brand = car.split(" ")[0].lower()
            track = config['TRACKS'][textNormalizer(sharedMemAPI.get_value('TrackName'))]
            layout = config['LAYOUTS'][textNormalizer(sharedMemAPI.get_value('LayoutName'))]
            
            latestData["state"] = f"{car} at {track} ({layout})"

            sessionType = sharedMemAPI.get_value('SessionType')
            match sessionType:
                case 0: session = "Practice"
                case 1: session = "Qualifying"
                case 2: session = "Race"
                case 3: session = "Warmup"

            if sharedMemAPI.get_value('GameInReplay'):
                latestData["details"] = f"Watching a {session} replay"
                latestData["end"] = None
            else:                
                match sessionType:
                    case 0:
                        personalBest = sharedMemAPI.get_value('LapTimeBestSelf')
                        if personalBest < 0:
                            personalBest = None
                        else:
                            pbSplit = str(timedelta(seconds=personalBest))[:-3].split(":")
                            personalBest = f"{pbSplit[1]}:{pbSplit[2]}"
                        latestData["details"] = f"{session} | PB: {personalBest}"
                    case 1 | 2 | 3:
                        latestData["details"] = f"{session} | P{sharedMemAPI.get_value('PositionClass')} of {sharedMemAPI.get_value('NumCars')}"

                if sharedMemAPI.get_value('SessionTimeRemaining') > 0.0 and sharedMemAPI.get_value('SessionPhase') >= 5:
                    latestData["end"] = math.ceil(time.time() + (sharedMemAPI.get_value('SessionTimeRemaining')))
                else:
                    latestData["end"] = None

            latestData["large_image"] = track.lower()
            latestData["large_text"] = track
            latestData["small_image"] = brand.lower()
            latestData["small_text"] = car

    return latestData