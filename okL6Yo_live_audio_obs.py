import sys, os, psutil
import subprocess

def is_process_running(exe_path):
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            # 检查进程的可执行文件路径是否匹配
            if proc.info['exe'] and os.path.samefile(proc.info['exe'], exe_path):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False
        
def copy_files_individually(src_dir, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dst_dir, file)
            shutil.copy2(src_file, dst_file)
            
this_file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(this_file_dir, "obs_audio_cache")
obs_cache_path = "c:\\obs"
obs_binary = "D:\\obs.exe"
if __name__ == '__main__':
    if is_process_running(obs_binary) == False:
        copy_files_individually(cache_dir, obs_cache_path)
        try:
            subprocess.run(['runas', '/user:Administrator', exe_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"启动obs失败 {e}")