import time,sys,os
import keyboard
from typing import Callable, Iterable, Union
sys.path.append(os.path.dirname(__file__))
import obsws_python as obs
from obsws_python.subs import Subs
from obsws_python.callback import Callback
import json
import threading
import queue
import random
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART'
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE'
class EventObserver:
    def __init__(self):
        self._curScene = "Scene_1"
        self._nextSources = queue.Queue()
        self._lock = threading.Lock()
        self._callback = Callback()
        self._curSource = ""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return
    
    def start(self, **kwargs):
        self._mediaPlayed = False
        self._event = obs.EventClient(**kwargs)
        kwargs["subs"] = 0
        self._request = obs.ReqClient(**kwargs)
        self._event.callback.register(
            [
                self.on_media_input_playback_started,
                self.on_media_input_playback_ended,
                self.on_current_program_scene_changed,
                self.on_exit_started,
            ]
        )

    def stop(self):
        self._event.disconnect()
        self._request.disconnect()

    def generate_transform(self, layer) :    
        for item in self._sceneLayers:
            if item['sourceName'] == layer :
                resp = self._request.get_scene_item_transform(self._curScene, item['sceneItemId'])
                # trans = resp.scene_item_transform
                trans = {}
                trans['rotation'] = random.randint(-5, 0)
                scale = random.uniform(1.0, 1.1)
                trans['scaleX'] = scale
                trans['scaleY'] = scale
                trans['positionY'] = random.randint(-600, 600)
                self._request.set_scene_item_transform(self._curScene, item['sceneItemId'], trans)
                break

    def on_media_input_playback_started(self, data):
        print('OBS current scene MediaInput: ' + data.input_name +' Playback Started')
        with self._lock:
            self._curSource = data.input_name
            # for item in self._sceneLayers:
            #     if item['sourceName'] == data.input_name :
            #         self._request.set_scene_item_index(self._curScene, item['sceneItemId'], len(self._sceneLayers))
            #         break
        print("OBS Set current layer to: " + data.input_name + " !!!!!!!!!!")

        self._callback.Trigger("onMediaInputPlaybackStarted", data)

    def move_to_next_video(self, name):
        self._curSource = ""
        if self._nextSources.qsize() > 0:
            nextSource = self._nextSources.get()
            self.generate_transform(nextSource)
            self._mediaPlayed = True
            print("Current Thread: " + str(threading.get_ident()) + ", source: " + nextSource + " Playback Restarted")
            for item in self._sceneLayers:
                if "product" in item['sourceName']:
                    if item['sourceName'] == nextSource:
                        self._request.set_scene_item_enabled(self._curScene, item['sceneItemId'], True)
                    else:
                        self._request.set_scene_item_enabled(self._curScene, item['sceneItemId'], False)
            if name is not None and name == nextSource:
                self._request.trigger_media_input_action(nextSource, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)
            # self._request.trigger_media_input_action(nextSource, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)
        else:
            self._mediaPlayed = False
    def on_media_input_playback_ended(self, data):
        print('OBS current scene MediaInput: ' + data.input_name +' Playback Ended')
        with self._lock:
            self.move_to_next_video(data.input_name)
        self._callback.Trigger("onMediaInputPlaybackEnded", data)

    def on_current_program_scene_changed(self, data):
        print(f"OBS Set current scene to: {data.scene_name} !!!!!!!!!!")
        with self._lock:
            if self._curScene != data.scene_name:
                self._curScene = data.scene_name
                self._sceneLayers = self._request.get_scene_item_list(self._curScene).scene_items
                self._nextSources = queue.Queue()

        self._callback.Trigger("onCurrentSceneChanged", data)

    def on_exit_started(self, _):
        print("OBS closing!")


class OBScriptManager :
    def __init__(self, port):
        self.port = port
        self.maxCommandNum = 1
        self._observer = EventObserver()
        self._isInitialized = False

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return

    def set_max_waiting_commands(self, num) :
        if num >= 0:
            self.maxCommandNum = num
    
    def register_lisenter(self, fns: Union[Iterable, Callable]):
        self._observer._callback.register(fns)

    # speed = 100 是正常速度， 最高是200 二倍速 
    # Todo 通过inputsetting修改视频倍速speed避免视频重播
    def set_current_layer_play_speed(self, speed):
        if self._observer._mediaPlayed == True :
            with self._observer._lock:
                if self._observer._mediaPlayed == True:
                    seekResp = self._observer._request.get_media_input_status(self._observer._curSource)
                    if seekResp.media_state == 'OBS_MEDIA_STATE_PLAYING':
                        self._observer._request.set_input_settings(self._observer._curSource, {"speed_percent" : speed}, True)
                        self._observer._request.set_media_input_cursor(self._observer._curSource, seekResp.media_cursor)

    def set_current_layer_queue(self, layer):
        print("Script Set Current Layer to: "+ layer)
        found = False
        with self._observer._lock:
            for item in self._observer._sceneLayers:
                if item['sourceName'] == layer:
                    found = True
                    break
            if found == False:
                print("Script Current source cound not found in Scene: " + layer)
                return False
            nextCount = self._observer._nextSources.qsize()
            if nextCount < self.maxCommandNum:
                self._observer._nextSources.put(layer)
            else:
                print("Script max waiting source list count is over than config: " + str(
                    self.maxCommandNum) + " !!! drop command: " + layer)
            if self._observer._mediaPlayed == False:
                self._observer.move_to_next_video(layer)
            return True
    
    def set_current_layer_direct(self, layer):
        print("Script Set Current Layer to: "+ layer)
        found = False
        with self._observer._lock:
            if self._observer._mediaPlayed == True:
                print("OBS video: " + self._observer._curSource + " is playing!!!!!!!!!!!!!!!")
                return False
            for item in self._observer._sceneLayers:
                if item['sourceName'] == layer :
                    found = True
                    break
            if found == False:
                print("Script Current source cound not found in Scene: " + layer)
                return False
            self._observer._mediaPlayed = True
            self._observer._request.trigger_media_input_action(layer, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)
            return True
        
    def flush_inputs(self):
        self._videoInputs = []
        response = self._observer._request.get_input_list()
        for input in response.inputs:
            if input["inputKind"] == 'ffmpeg_source' : #视频源输入
                settingResp = self._observer._request.get_input_settings(input["inputName"])
                settings : dict = settingResp.input_settings 
                #视频源的循环模式一定关闭，不然无法触发on_media_input_playback_ended事件
                if input["inputName"] != "background" :
                    self._observer._request.set_input_settings(input["inputName"], {"looping" : False, "speed_percent" : 100}, True)
                # if settings.get('looping') is None or settings["looping"] == True :
                settings["looping"] = False 
                settings["inputName"] = input["inputName"]
                self._videoInputs.append(settings)
        return self._videoInputs
    
    def flush_scenes(self):
        response = self._observer._request.get_scene_list()
        self._sceneList = response.scenes
        self._observer._curScene = response.current_program_scene_name
        return self._sceneList
    
    def set_current_scene(self, scene_name) :
        print("Script Set Current Scene to: "+ scene_name)
        found = False
        for item in self._sceneList:
            if item['sceneName'] == scene_name :
                found = True
                break
        if found == False:
            print("Script Current Scene cound not be found: " + scene_name)
            return False

        sceneLayers = self._observer._request.get_scene_item_list(scene_name).scene_items

        with self._observer._lock :
            self._observer._curScene = scene_name
            self._observer._nextSources = queue.Queue()
            self._observer._mediaPlayed = False
            self._observer._request.set_current_program_scene(scene_name)
            self._observer._sceneLayers = sceneLayers
        
        return True

    def clear_layer_queue(self):
        with self._observer._lock :
            self._observer._nextSources = queue.Queue()

    def start(self):
        if self._isInitialized == False:
            ekwargs = {
                "port": self.port,
                "subs" :Subs.MEDIAINPUTS | Subs.SCENES
            }
            self._observer.start(**ekwargs)
            self._isInitialized = True
            self.flush_scenes()
            self.flush_inputs()
            self.set_current_scene(self._observer._curScene)

    def stop(self):
        self._observer.stop()
        self._isInitialized = False


def run(scriptMgr):
    keyboard.add_hotkey("1", scriptMgr.set_current_layer_queue, args=("product_1",))
    keyboard.add_hotkey("2", scriptMgr.set_current_layer_queue, args=("product_2",))
    keyboard.add_hotkey("3", scriptMgr.set_current_layer_queue, args=("product_3",))
    keyboard.add_hotkey("4", scriptMgr.set_current_layer_queue, args=("product_4",))
    keyboard.add_hotkey("5", scriptMgr.set_current_layer_queue, args=("product_5",))
    # keyboard.add_hotkey("5", scriptMgr.set_current_scene, args=("Scene_1",))
    # keyboard.add_hotkey("6", scriptMgr.set_current_scene, args=("Scene_2",))
    # keyboard.add_hotkey("0", scriptMgr.set_current_layer_play_speed, args=(200,))
    scriptMgr.start()
    while True:
        # if scriptMgr._observer._curSource != "" :
        #     resp = scriptMgr._observer._request.get_media_input_status(scriptMgr._observer._curSource)
        #     if resp.media_state == 'OBS_MEDIA_STATE_PLAYING':
        #         print("OBS Media playing " + scriptMgr._observer._curSource + " timestamp:" + str(resp.media_cursor) + " ms, duration:" + str(resp.media_duration) + " ms")
        if keyboard.is_pressed('q'):
            print("Exiting the OBScriptManager work, Disconnnect from obs !!!!!!!.")
            scriptMgr.stop()
            break
        time.sleep(0.03) 

if __name__ == "__main__":
    port = 4455 #obs 工具-》WebSocket服务器设置-》服务端端口，默认是4455，本地不开启身份认证
    # 脚本启动前，应把本地OBS的所有scene和source都配置好
    # 脚本目前只负责scene和source的切换和控制
    with OBScriptManager(port) as mgr:
       run(mgr)