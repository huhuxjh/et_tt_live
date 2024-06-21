import sys, os, psutil, shutil
import subprocess

def is_process_running(name, keyword):
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            if name in proc.info['name'] and keyword in proc.info['cmdline']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def copy_files_recursively(src_dir, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for root, dirs, files in os.walk(src_dir):
        relative_path = os.path.relpath(root, src_dir)
        dst_sub_dir = os.path.join(dst_dir, relative_path)

        if not os.path.exists(dst_sub_dir):
            os.makedirs(dst_sub_dir)
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dst_sub_dir, file)
            shutil.copy2(src_file, dst_file)

this_file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(this_file_dir, "obs_audio_cache")
obs_cache_path = "C:\\Users\\1\\AppData\\Roaming\\obs-studio"
exe_path = "D:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"
keyword = "audio"
if __name__ == '__main__':
    if is_process_running("obs64.exe", keyword) == False:
        copy_files_recursively(cache_dir, obs_cache_path)
        try:
            subprocess.Popen([exe_path, keyword], cwd=os.path.dirname(exe_path), creationflags=subprocess.CREATE_NEW_CONSOLE)
        except subprocess.CalledProcessError as e:
            print(f"启动obs失败 {e}")