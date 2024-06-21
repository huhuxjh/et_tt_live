import sys, os, psutil, shutil
import subprocess
import okL6Yo_live_audio_obs

this_file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(this_file_dir, "obs_video_cache")
obs_cache_path = "C:\\Users\\1\\AppData\\Roaming\\obs-studio"
exe_path = "D:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"
keyword = "video"
if __name__ == '__main__':
    if okL6Yo_live_audio_obs.is_process_running("obs64.exe", keyword) == False:
        okL6Yo_live_audio_obs.copy_files_recursively(cache_dir, obs_cache_path)
        try:
            subprocess.Popen([exe_path, keyword], cwd=os.path.dirname(exe_path), creationflags=subprocess.CREATE_NEW_CONSOLE)
        except subprocess.CalledProcessError as e:
            print(f"启动obs失败 {e}")
