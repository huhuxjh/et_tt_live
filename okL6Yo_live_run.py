import sys, os
import subprocess
this_file_dir = os.path.dirname(os.path.abspath(__file__))

et_tt_live_code = 'D:\\path'
local_video_dir = "D:\\video_res"
llm_api_main_py = 'D:\\path\\to\\your_script.py'

sys.path.append(et_tt_live_code)
from remote_config.et_service_util import ver_async
import main as main

def start_llm_service():
    if await ver_async() == False:
        subprocess.Popen(['python', llm_api_main_py], creationflags=subprocess.CREATE_NEW_CONSOLE)

def process_video_rotate(path="D:\\video_res"):
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_process_video_rotate.py"), path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
def start_obs():
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_audio_obs.py")], creationflags=subprocess.CREATE_NEW_CONSOLE)
    subprocess.Popen(['python', os.path.join(this_file_dir,"okL6Yo_live_video_obs.py")], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
if __name__ == '__main__':
    start_llm_service()
    process_video_rotate(local_video_dir)
    start_obs()
    run_mode = sys.argv[1]
    main.process("okL6Yo", "B1:B10", 4456, 4455, run_mode, local_video_dir)