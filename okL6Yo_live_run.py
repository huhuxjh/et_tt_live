import sys, os
import subprocess
import time

this_file_dir = os.path.dirname(os.path.abspath(__file__))

et_tt_live_code = 'E:\\et_tt_live'
local_video_dir = "D:\\video_res"
llm_api_bat = 'E:\\ET_TTS\\run_daemon.bat'

sys.path.append(et_tt_live_code)
from remote_config.et_service_util import ver_async
import main as main

def start_llm_service():
    if ver_async() == False:
        subprocess.Popen([llm_api_bat], cwd=os.path.dirname(llm_api_bat), creationflags=subprocess.CREATE_NEW_CONSOLE)

def process_video_rotate(path="D:\\video_res"):
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_process_video_rotate.py"), path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
def start_obs():
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_audio_obs.py")], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(5)
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_video_obs.py")], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
if __name__ == '__main__':
    start_llm_service()
    process_video_rotate(local_video_dir)
    start_obs()
    while ver_async() == False:
        print("等待llm啓動")
        time.sleep(3)
    run_mode = sys.argv[1]
    main.process("okL6Yo", "B1:B10", 4456, 4455, run_mode, local_video_dir)