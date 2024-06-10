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
from pathlib import Path
from template_generator import ffmpeg as template_ffmpeg
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART'
OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE'
OBS_MEDIA_WAV_NAME = "wav"
OBS_MEDIA_VIDEO_NAME = "video"

OBS_MEDIA_VIDEO_EFFECT_KIND = "filter-custom"
OBS_MEDIA_VIDEO_EFFECT_1 = "ZoomIn"
OBS_MEDIA_VIDEO_EFFECT_2 = "ZoomOutIn"
class EventObserver:
    def __init__(self, effect_dir, add_filter):
        self._control_layers = []
        self._sceneLayers = []
        self._curScene = ""
        self._curSceneWidth = 0
        self._curSceneHeight = 0
        self.add_filter = add_filter
        self._effect_dir = effect_dir
        self._effects = []
        self.video_callback = None
        self.audio_callback = None
        self._lock = threading.Lock()
        self._playingSources = set()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return
    
    def start(self, **kwargs):
        self._event = obs.EventClient(**kwargs)
        kwargs["subs"] = 0
        self._request = obs.ReqClient(**kwargs)
        self._event.callback.register([
                self.on_media_input_playback_started,
                self.on_media_input_playback_ended,
                self.on_current_program_scene_changed,
                self.on_exit_started,
            ])
        response = self._request.get_scene_list()
        self._curScene = response.current_program_scene_name
        video_setting = self._request.get_video_settings()
        self._curSceneWidth = video_setting.base_width
        self._curSceneHeight = video_setting.base_height
        self._sceneLayers = self._request.get_scene_item_list(self._curScene).scene_items

    def play_audio(self, wav, audio_callback):
        self.audio_callback = audio_callback
        if self.has_source(OBS_MEDIA_WAV_NAME) == False:
            self._request.create_input(self._curScene, OBS_MEDIA_WAV_NAME, "ffmpeg_source", {
                "local_file": "",
                "is_local_file": True,
                "looping": False
            }, True)
        self._request.set_input_settings(OBS_MEDIA_WAV_NAME, {
            "local_file": wav,
            "looping": False
            }, True)
        for item in self._sceneLayers:
            if item['sourceName'] == OBS_MEDIA_WAV_NAME:
                self._request.set_scene_item_enabled(self._curScene, item['sceneItemId'], True)
                self._request.trigger_media_input_action(OBS_MEDIA_WAV_NAME, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)

    def stop(self):
        self._event.disconnect()
        self._request.disconnect()

    def on_media_input_playback_started(self, data):
        print(str(time.time()) + '[OBS] ' + data.input_name +' play start')
        with self._lock:
            self._playingSources.add(self._curScene + "_" + data.input_name)
            # for item in self._sceneLayers:
            #     if item['sourceName'] == data.input_name :
            #         self._request.set_scene_item_index(self._curScene, item['sceneItemId'], len(self._sceneLayers))
            #         break

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
        # 视频创建时一次性加载_effect_dir下所有的自定义的特效
        if self._effect_dir is not None and os.path.isdir(self._effect_dir):
            all_effects = os.listdir(self._effect_dir)
            for effect in all_effects:
                if os.path.isfile(os.path.join(self._effect_dir, effect)) and os.path.join(self._effect_dir, effect).lower().endswith('.effect'):
                    name = Path(effect).stem
                    self._request.create_source_filter(key, name, OBS_MEDIA_VIDEO_EFFECT_KIND, {
                        'effect_path': os.path.join(self._effect_dir, effect),
                        "iTime" : 999.0
                    })
                    self._effects.append(name)
        self._sceneLayers = self._request.get_scene_item_list(self._curScene).scene_items
    
    def update_input(self, key, mp4):
        if key not in self._control_layers:
            self._control_layers.append(key)
        self._request.set_input_settings(key, {
            "local_file": mp4,
            "looping": False
        }, True)

    def play_video(self, key, source_config, video_callback):
        self.video_callback = video_callback
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
                print(str(time.time()) + "=========== start play")
                self._request.trigger_media_input_action(key, OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART)
                return True
        return False
        
    def on_media_input_playback_ended(self, data):
        print(str(time.time()) + '[OBS] ' + data.input_name + " play end")
        with self._lock:
            for item in self._sceneLayers:
                if item['sourceName'] == data.input_name and (item["sourceName"] in self._control_layers):
                    if self.video_callback:
                        self.video_callback()
                elif item['sourceName'] == data.input_name and item["sourceName"] == OBS_MEDIA_WAV_NAME:
                    if self.audio_callback:
                        self.audio_callback()
            self._playingSources.discard(self._curScene + "_" + data.input_name)

    def on_current_program_scene_changed(self, data):
        print(f"[OBS] on_current_program_scene_changed: {data.scene_name}")
        with self._lock:
            if self._curScene != data.scene_name:
                self._curScene = data.scene_name
                self._sceneLayers = self._request.get_scene_item_list(self._curScene).scene_items

    def on_exit_started(self, _):
        print("[OBS] closing!")

class OBScriptManager :
    # video_port ： obs 视频端口
    # audio_port ： obs 音频端口
    # sub_tag_dir ： 要播放的视频标签的路径
    # effect_dir ： 切换视频时的入场动画的资源目录, 初次加载时需要打开obs，并在[工具]-》[脚本]-》加载 CustomShaders.lua,否则obs无法创建OBS_MEDIA_VIDEO_EFFECT_KIND类型的effect
    # add_filter ： 是否添加绿幕抠图滤镜
    def __init__(self, video_port, audio_port, sub_tag_dir, effect_dir = None, add_filter=False):
        self.video_port = video_port
        self.audio_port = audio_port
        self._video_observer = EventObserver(effect_dir, add_filter)
        self._audio_observer = EventObserver(effect_dir, add_filter)
        self._isInitialized = False
        self._curPlayingVideo = ""
        self.tags = {}
        if os.path.isdir(sub_tag_dir):
            all_tags = os.listdir(sub_tag_dir)
            for tag in all_tags:
                self.tags[tag] = []
                if os.path.isfile(os.path.join(sub_tag_dir, tag)):
                    # w,h,bitrate,fps,video_duration = template_ffmpeg.videoInfo(os.path.join(sub_tag_dir, tag), "")
                    self.tags[tag].append({
                        "path": os.path.join(sub_tag_dir, tag),
                        # "width": w,
                        # "height": h,
                        # "duration": video_duration,
                        "played": False
                    })
                elif os.path.isdir(os.path.join(sub_tag_dir, tag)):
                    all_files = os.listdir(os.path.join(sub_tag_dir, tag))
                    all_files = [f for f in all_files if f.lower().endswith(('.mp4', '.mov', '.avi'))]
                    for f in all_files:
                        # w,h,bitrate,fps,video_duration = template_ffmpeg.videoInfo(os.path.join(sub_tag_dir, tag, f), "")
                        self.tags[tag].append({
                            "path": os.path.join(sub_tag_dir, tag, f),
                            # "width": w,
                            # "height": h,
                            # "duration": video_duration,
                            "played": False
                        })
                
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        return
    
    def get_play_tag_list(self, tag):
        if tag not in self.tags:
            return []
        return self.tags[tag]
    
    def get_video_status(self):
        try:
            if len(self._curPlayingVideo) > 0:
                resp = self._video_observer._request.get_media_input_status(self._curPlayingVideo)
                if resp.media_state == 'OBS_MEDIA_STATE_PLAYING':
                    return resp.media_cursor / 1000.0, resp.media_duration / 1000.0
        except:
            pass
        return 0, 0
    
    def get_audio_status(self):
        try:
            resp = self._audio_observer._request.get_media_input_status(OBS_MEDIA_WAV_NAME)
            if resp.media_state == 'OBS_MEDIA_STATE_PLAYING':
                return resp.media_cursor / 1000.0, resp.media_duration / 1000.0
        except:
            pass
        return 0, 0
    
    # 开始录制输出的obs，目前音频的obs即是最终的输出obs
    def startRecord(self):
        self._audio_observer._request.start_record()
    # 结束录制输出的obs
    # 返回值是录制完的视频的保存路径
    def stopRecord(self):
        response = self._audio_observer._request.stop_record()
        if response is not None and response.output_path is not None:
            return response.output_path
        return ""

    # effect ：动画枚举名称
    #          OBS_MEDIA_VIDEO_EFFECT_1 缩小动画
    #          OBS_MEDIA_VIDEO_EFFECT_2 放大-》缩小动画
    # duration : 动画时长(秒为单位)
    def play_effect(self, effect, duration):
        if effect in self._video_observer._effects:
            self._video_observer._request.set_source_filter_settings(self._curPlayingVideo, effect, {
                "duration" : duration,
                "iTime" : 0.0
            }, True)
    
    def play_video(self, tag, mp4=None, callback=None):
        print("[OBS-Control] play tag "+ tag)
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
        if 'width' not in play_mp4:
            w,h,bitrate,fps,video_duration = template_ffmpeg.videoInfo(play_mp4["path"], "")
            play_mp4["width"] = w
            play_mp4["height"] = h
            play_mp4["duration"] = video_duration
        if self._video_observer.has_source(OBS_MEDIA_VIDEO_NAME) == False:
            self._video_observer.create_input(OBS_MEDIA_VIDEO_NAME, play_mp4["path"])
        else:
            self._video_observer.update_input(OBS_MEDIA_VIDEO_NAME, play_mp4["path"])
        with self._video_observer._lock:
            self._curPlayingVideo = OBS_MEDIA_VIDEO_NAME
            self._video_observer.play_video(OBS_MEDIA_VIDEO_NAME, play_mp4, callback)
            return True
    
    def play_audio(self, wav, callback=None):
        with self._audio_observer._lock:
            self._audio_observer.play_audio(wav, callback)
            return True

    def start(self):
        if self._isInitialized == False:
            ekwargs = {
                "port": self.video_port,
                "subs" :Subs.MEDIAINPUTS | Subs.SCENES
            }
            self._video_observer.start(**ekwargs)
            ekwargs1 = {
                "port": self.audio_port,
                "subs" :Subs.MEDIAINPUTS | Subs.SCENES
            }
            self._audio_observer.start(**ekwargs1)
            self._isInitialized = True

    def stop(self):
        if self._isInitialized:
            self._video_observer.stop()
            self._audio_observer.stop()
            self._isInitialized = False

    def is_playing(self) :
        return len(self._video_observer._playingSources) > 0
    
if __name__ == "__main__":
    #obs 工具-》WebSocket服务器设置-》服务端端口，默认是4455，本地不开启身份认证
    # 脚本启动前，应把本地OBS的所有scene和source都配置好
    # 脚本目前只负责scene和source的切换和控制
    scriptMgr = OBScriptManager(4455, 4455, "D:\\video_normal", "D:/code/et_tt_live/obs/obs_effect/", False)
    scriptMgr.start()
    print(scriptMgr.get_play_tag_list("discount_now"))
    idx = 0
    def video_callback():
        print("======================= video end")
    def audio_callback():
        print("======================= audio end")
    while True:
        if scriptMgr.is_playing():
            print("======================= 上一个未播完，等待下一次")
            time.sleep(2)
            continue
            
        tag = random.choice(["discount_in_live", "discount_now"])
        # if idx > 3:
        #     idx = 0
        # wav = ["D:\\audios\\tts_2_0.wav","D:\\audios\\tts_18_0.wav","D:\\audios\\tts_44_0.wav","D:\\audios\\tts_56_0.wav"][idx]
        print("======================= play")
        # print("======================= audio " + wav)
        print("======================= video " + tag)
        scriptMgr.play_video(tag, None, video_callback)
        scriptMgr.play_effect(OBS_MEDIA_VIDEO_EFFECT_2, 4.0)
        # scriptMgr.play_audio(wav, audio_callback)
        time.sleep(2)
        # v1, v2 = scriptMgr.get_audio_status()
        # print("======================= audio 进度：" + str(v1) + "," + str(v2))
        v1, v2 = scriptMgr.get_video_status()
        print("======================= video 进度：" + str(v1) + "," + str(v2))
        time.sleep(2)
        idx += 1