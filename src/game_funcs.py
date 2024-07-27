import sys, os, time, math
from datetime import timedelta
from pyaccsharedmemory import ACC_SESSION_TYPE, ACC_STATUS

def build_path(relative):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative)

def getAccTelemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.read_shared_memory()

    if telemetry != None:
        match telemetry.Graphics.status:
            case ACC_STATUS.ACC_OFF:
                latestData["state"] = "In menus"
                latestData["details"] = None
                latestData["end"] = None
                latestData["large_image"] = "acc_logo"
                latestData["large_text"] = None
                latestData["small_image"] = None
                latestData["small_text"] = None
            case ACC_STATUS.ACC_REPLAY:
                car = config['CARS'][telemetry.Static.car_model.replace("\x00", "").lower()]
                brand = car.split(" ")[0].lower()
                track = config['TRACKS'][telemetry.Static.track.replace("\x00", "").lower()]

                latestData["state"] = f"{car} at {track}"
                latestData["details"] = f"Watching a {telemetry.Graphics.session_type} replay"
                latestData["end"] = None
                latestData["large_image"] = track.lower()
                latestData["large_text"] = track
                latestData["small_image"] = brand.lower()
                latestData["small_text"] = car
            case ACC_STATUS.ACC_LIVE | ACC_STATUS.ACC_PAUSE:
                car = config['CARS'][telemetry.Static.car_model.replace("\x00", "").lower()]
                brand = car.split(" ")[0].lower()
                track = config['TRACKS'][telemetry.Static.track.replace("\x00", "").lower()]

                latestData["state"] = f"{car} at {track}"
                pb_split = telemetry.Graphics.best_time_str.replace("\x00", "").split(":")
                if pb_split[0] == "35791":
                    personal_best = None
                else:
                    personal_best = f"{pb_split[0]}:{pb_split[1]}.{pb_split[2]}"
                
                match telemetry.Graphics.session_type:
                    case ACC_SESSION_TYPE.ACC_PRACTICE | \
                            ACC_SESSION_TYPE.ACC_HOTLAP | \
                            ACC_SESSION_TYPE.ACC_HOTLAPSUPERPOLE | \
                            ACC_SESSION_TYPE.ACC_HOTSTINT:
                        latestData["details"] = f"{telemetry.Graphics.session_type} | PB: {personal_best}"
                    case ACC_SESSION_TYPE.ACC_QUALIFY | \
                            ACC_SESSION_TYPE.ACC_RACE:
                        latestData["details"] = f"{telemetry.Graphics.session_type} | P{telemetry.Graphics.position} of {telemetry.Static.num_cars}"
                
                if telemetry.Graphics.session_time_left > 0.0:
                    latestData["end"] = math.ceil(time.time() + (telemetry.Graphics.session_time_left/1000))
                else:
                    latestData["end"] = None
                
                latestData["large_image"] = track.lower()
                latestData["large_text"] = track
                latestData["small_image"] = brand.lower()
                latestData["small_text"] = car

    return latestData

def getLmuTelemetry(sharedMemAPI, config):
    latestData = {}
    telemetry = sharedMemAPI.isSharedMemoryAvailable()

    if telemetry != None:
        if sharedMemAPI.Rf2Scor.mScoringInfo.mSession == 0 or sharedMemAPI.isTrackLoaded() == 0:
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
                parsedCar = sharedMemAPI.playersVehicleScoring().mVehicleName.decode("utf-8").split((":"))[0].replace("#", "").replace("'", "").replace(" ", "_")
            car = config['CARS'][parsedCar]
            brand = car.split(" ")[0].lower()
            track = config['TRACKS'][sharedMemAPI.Rf2Scor.mScoringInfo.mTrackName.decode("utf-8").lower().replace(" ", "_")]
            
            latestData["state"] = f"{car} at {track}"
            
            if sharedMemAPI.Rf2Scor.mScoringInfo.mServerPublicIP != 0:
                onOff = "Online"
            else:
                onOff = "Offline"

            if sharedMemAPI.Rf2Scor.mScoringInfo.mSession < 5:
                personalBest = sharedMemAPI.playersVehicleScoring().mBestLapTime
                if personalBest < 0:
                    personalBest = None
                else:
                    pbSplit = str(timedelta(seconds=personalBest))[:-3].split(":")
                    personalBest = f"{pbSplit[1]}:{pbSplit[2]}"
                latestData["details"] = f"{onOff} Practice | PB: {personalBest}"
            else:
                if sharedMemAPI.Rf2Scor.mScoringInfo.mSession < 9:
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
        if sharedMemAPI.get_value('GameInMenus'):
            latestData["state"] = "In menus"
            latestData["details"] = None
            latestData["end"] = None
            latestData["large_image"] = "r3e_logo"
            latestData["large_text"] = None
            latestData["small_image"] = None
            latestData["small_text"] = None
        elif sharedMemAPI.get_value('GameInReplay'):
            car = sharedMemAPI.get_value('VehicleInfo.Name')
            brand = car.split(" ")[0].lower()
            track = sharedMemAPI.get_value('TrackName')
            layout = sharedMemAPI.get_value('LayoutName')

            latestData["state"] = f"{car} at {track} ({layout})"
            latestData["details"] = f"Watching a {sharedMemAPI.get_value('SessionType')} replay"
            latestData["end"] = None
            latestData["large_image"] = track.lower()
            latestData["large_text"] = track
            latestData["small_image"] = brand.lower()
            latestData["small_text"] = car
        elif sharedMemAPI.get_value('SessionType') >= 0:
            car = sharedMemAPI.get_value('VehicleInfo.Name')
            brand = car.split(" ")[0].lower()
            track = sharedMemAPI.get_value('TrackName')
            layout = sharedMemAPI.get_value('LayoutName')

            latestData["state"] = f"{car} at {track} ({layout})"
            personal_best = str(timedelta(seconds=sharedMemAPI.get_value('LapTimeBestSelf')))
            if "-1 day" in personal_best:
                personal_best = None
            
            match sharedMemAPI.get_value('SessionType'):
                case 0 | 3:
                    latestData["details"] = f"{sharedMemAPI.get_value('SessionType')} | PB: {personal_best}"
                case 1 | 2:
                    latestData["details"] = f"{sharedMemAPI.get_value('SessionType')} | P{sharedMemAPI.get_value('PositionClass')} of {sharedMemAPI.get_value('NumCars')}"

            if sharedMemAPI.get_value('SessionTimeRemaining') > 0.0:
                latestData["end"] = math.ceil(time.time() + (sharedMemAPI.get_value('SessionTimeRemaining')/1000))
            else:
                latestData["end"] = None

            latestData["large_image"] = track.lower()
            latestData["large_text"] = track
            latestData["small_image"] = brand.lower()
            latestData["small_text"] = car

    return latestData