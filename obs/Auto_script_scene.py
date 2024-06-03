import time
import keyboard
import obsws_python as obs
from obsws_python.subs import Subs
import json
import threading
import queue
class EventObserver:
    def __init__(self, **kwargs):
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
        self.running = True
        self.mediaEnded = True
        self.nextSceneList = queue.Queue()
        self.lock = threading.RLock()
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._event.disconnect()
        self._request.disconnect()
    def on_media_input_playback_started(self, data):
        self.lock.acquire()
        # print("EventClient EventObserver The current scene on_MediaInputPlaybackStarted")
        self.mediaEnded = False
        self.lock.release()
    def on_media_input_playback_ended(self, data):
        self.lock.acquire()
        print("The current scene video play Finish !!!!!!!!!!")
        self.mediaEnded = True
        if self.nextSceneList.qsize() > 0:
            nextScene = self.nextSceneList.get()
            self._request.set_current_program_scene(nextScene)
            print("The current BOS Start to next scene:" + nextScene + "!!!!!!!!!!")
        self.lock.release()
    def on_current_program_scene_changed(self, data):
        print(f"OBS Switched to scene: {data.scene_name} done!!!!!!!!!!")
    def on_exit_started(self, _):
        print("OBS closing!")
        self.running = False


class ScriptMgr :
    def __init__(self, port):
        ekwargs = {
            "port": port,
            "subs" :Subs.MEDIAINPUTS | Subs.SCENES
        }
        self._observer = EventObserver(**ekwargs)
        rkwargs = {
            "port": port
        }
        self._request = obs.ReqClient(**rkwargs)
        keyboard.add_hotkey("1", self.set_layer, args=("Scene_1",))
        keyboard.add_hotkey("2", self.set_layer, args=("Scene_2",))
        keyboard.add_hotkey("3", self.set_layer, args=("Scene_3",))
        keyboard.add_hotkey("4", self.set_layer, args=("Scene_4",))

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._request.disconnect()
        return
    
    def set_layer(self, scene):
        print("Script Get Keyboard Signal Switched to scene:"+ scene)
        self._observer.lock.acquire()
        nextCount = self._observer.nextSceneList.qsize()
        if nextCount > 0 or self._observer.mediaEnded == False:
            if nextCount < 5:
                self._observer.nextSceneList.put(scene)
            else:
                print("Script Get Keyboard Signal out of max waiting scene list count: 5 !!! drop signal " + scene)
            self._observer.lock.release()
            return False
        else:
            resp = self._request.set_current_program_scene(scene)
            self._observer.lock.release()
            return True
    
    def get_layer(self):
        resp = self._request.get_scene_item_list("Scene_1")
        print()

    def run(self):
        while True:
            if keyboard.is_pressed('q'):
                print("Exiting the loop.")
                break
            time.sleep(0.1) 

if __name__ == "__main__":
    with ScriptMgr(4400) as mgr:
        mgr.run()