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
from template_generator import ffmpeg as template_ffmpeg
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART'
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE'

class EventObserver:
    def __init__(self, add_filter):
        self._control_layers = []
        self._curScene = ""
        self._curSceneWidth = 0
        self._curSceneHeight = 0
        self.add_filter = add_filter
        self._lock = threading.Lock()
        self._callback = Callback()
        self._playingSources = set()
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return
    
    def start(self, **kwargs):
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

    def on_media_input_playback_started(self, data):
        print('OBS current scene MediaInput: ' + data.input_name +' Playback Started')
        with self._lock:
            self._playingSources.add(self._curScene + "_" + data.input_name)
            # for item in self._sceneLayers:
            #     if item['sourceName'] == data.input_name :
            #         self._request.set_scene_item_index(self._curScene, item['sceneItemId'], len(self._sceneLayers))
            #         break
        self._callback.Trigger("onMediaInputPlaybackStarted", data)

    def has_source(self, key):
        all_inputs = self._request.get_input_list()        
        for inp in all_inputs.inputs:
            if inp["inputName"] == key and (inp["inputKind"] == 'ffmpeg_source' or inp["inputKind"] == 'vlc_source') :
                return True
        return False
        
    def create_input(self, key, mp4):
        self._control_layers.append(key)
        self._request.create_input(self._curScene, key, "ffmpeg_source", {
            "local_file": mp4,
            "is_local_file": True,
            "looping": False
        }, False)
        if self.add_filter:
            self._request.create_source_filter(key, "色度键", "chroma_key_filter_v2", {
                'similarity':412,
                'smoothness':88,
                'spill':10
            })
    
    def update_input(self, key, mp4):
        if key not in self._control_layers:
            self._control_layers.append(key)
        self._request.set_input_settings(key, {
            "local_file": mp4,
            "looping": False
        }, True)
        
    def play_source(self, key, source_config):
        self._playingSources.add(self._curScene + "_" + key)
        for item in self._sceneLayers:
            if item['sourceName'] == key:
                trans = {}
                trans['rotation'] = 0
                base_scale = self._curSceneWidth / source_config["width"]
                scale = random.uniform(base_scale, base_scale*1.1)
                trans['scaleX'] = scale
                trans['scaleY'] = scale
                trans['positionY'] = self._curSceneHeight/2 - source_config["height"] / 2 * base_scale
                trans['positionX'] = self._curSceneWidth/2 - source_config["width"] / 2 * base_scale
                self._request.set_scene_item_transform(self._curScene, item['sceneItemId'], trans)
                self._request.set_scene_item_enabled(self._curScene, item['sceneItemId'], True)
                self._request.trigger_media_input_action(key, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)
        
    def on_media_input_playback_ended(self, data):
        print('OBS current scene MediaInput: ' + data.input_name +' Playback Ended')
        with self._lock:
            for item in self._sceneLayers:
                if item['sourceName'] == data.input_name and item["sourceName"] in self._control_layers:
                    self._request.set_scene_item_enabled(self._curScene, item['sceneItemId'], False)
                    break
            self._playingSources.discard(self._curScene + "_" + data.input_name)
        self._callback.Trigger("onMediaInputPlaybackEnded", data)

    def on_current_program_scene_changed(self, data):
        print(f"OBS Set current scene to: {data.scene_name} !!!!!!!!!!")
        with self._lock:
            if self._curScene != data.scene_name:
                self._curScene = data.scene_name
                self._sceneLayers = self._request.get_scene_item_list(self._curScene).scene_items

        self._callback.Trigger("onCurrentSceneChanged", data)

    def on_exit_started(self, _):
        print("OBS closing!")

class OBScriptManager :
    def __init__(self, port, sub_tag_dir, add_filter):
        self.port = port
        self.maxCommandNum = 1
        self._observer = EventObserver(add_filter)
        self._isInitialized = False
        self.tags = {}
        if os.path.isdir(sub_tag_dir):
            all_tags = os.listdir(sub_tag_dir)
            for tag in all_tags:
                self.tags[tag] = []
                if os.path.isfile(os.path.join(sub_tag_dir, tag)):
                    w,h,bitrate,fps,video_duration = template_ffmpeg.videoInfo(os.path.join(sub_tag_dir, tag), "")
                    self.tags[tag].append({
                        "path": os.path.join(sub_tag_dir, tag),
                        "width": w,
                        "height": h,
                        "duration": video_duration,
                        "played": False
                    })
                elif os.path.isdir(os.path.join(sub_tag_dir, tag)):
                    all_files = os.listdir(os.path.join(sub_tag_dir, tag))
                    all_files = [f for f in all_files if f.lower().endswith(('.mp4', '.mov', '.avi'))]
                    for f in all_files:
                        w,h,bitrate,fps,video_duration = template_ffmpeg.videoInfo(os.path.join(sub_tag_dir, tag, f), "")
                        self.tags[tag].append({
                            "path": os.path.join(sub_tag_dir, tag, f),
                            "width": w,
                            "height": h,
                            "duration": video_duration,
                            "played": False
                        })
                
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return
    
    def register_lisenter(self, fns: Union[Iterable, Callable]):
        self._observer._callback.register(fns)
    
    def get_play_tag_list(self, tag):
        if tag not in self.tags:
            return []
        return self.tags[tag]
    
    def get_play_status(self, tag):
        resp = scriptMgr._observer._request.get_media_input_status(tag)
        if resp.media_state == 'OBS_MEDIA_STATE_PLAYING':
            return resp.media_cursor, resp.media_duration
    
    def play(self, tag, mp4=None):
        if self.is_playing() == True:
            return False
        print("play tag "+ tag)
        if tag not in self.tags:
            return False
        if mp4:
            for f in self.tags[tag]:
                if f["path"] == mp4:
                    play_mp4 = f
                    break
        else:
            has_files = [f for f in self.tags[tag] if f["played"]==False]
            if len(has_files) == 0:
                for f in self.tags[tag]:
                    f["played"] = False
                play_mp4 = random.choice(self.tags[tag])
            else:
                play_mp4 = random.choice(has_files)
            play_mp4["played"] = True
        self.set_layer_source(tag, play_mp4["path"])
        with self._observer._lock:
            if len(self._observer._playingSources) > 0:
                print("OBS Current scene layer video is playing: " + str(self._observer._playingSources))
                return False
            self._observer.play_source(tag, play_mp4)
            return True
    
    def set_layer_source(self, layer, source):
        if self._observer.has_source(layer) == False:
            self._observer.create_input(layer, source)
            self.update_current_scene(self._observer._curScene)
        else:
            self._observer.update_input(layer, source)
    
    def flush_scenes(self):
        response = self._observer._request.get_scene_list()
        self._sceneList = response.scenes
        with self._observer._lock:
            self._observer._curScene = response.current_program_scene_name
        return self._sceneList
    
    def update_current_scene(self, scene_name) :
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
        video_setting = self._observer._request.get_video_settings()
        with self._observer._lock:
            self._observer._curScene = scene_name
            self._observer._curSceneWidth = video_setting.base_width
            self._observer._curSceneHeight = video_setting.base_height
            self._observer._sceneLayers = sceneLayers
            self._observer._request.set_current_program_scene(scene_name)
        
        return True

    def start(self):
        if self._isInitialized == False:
            ekwargs = {
                "port": self.port,
                "subs" :Subs.MEDIAINPUTS | Subs.SCENES
            }
            self._observer.start(**ekwargs)
            self._isInitialized = True
            self.flush_scenes()
            self.update_current_scene(self._observer._curScene)

    def stop(self):
        if self._isInitialized:
            self._observer.stop()
            self._isInitialized = False

    def is_playing(self) :
        return len(self._observer._playingSources) > 0
    
if __name__ == "__main__":
    obs_port = 4455 #obs 工具-》WebSocket服务器设置-》服务端端口，默认是4455，本地不开启身份认证
    # 脚本启动前，应把本地OBS的所有scene和source都配置好
    # 脚本目前只负责scene和source的切换和控制
    scriptMgr = OBScriptManager(obs_port, "D:\\video_normal", True)
    scriptMgr.start()
    print(scriptMgr.get_play_tag_list("discount_now"))
    while True:
        scriptMgr.play(random.choice(["discount_in_live", "discount_now"]), None)
        time.sleep(10)