import sys, os
import subprocess
from template_generator import ffmpeg as template_ffmpeg

def get_rotation_metadata(video_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=tags:stream_tags=rotate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        rotation = result.stdout.strip()
        if rotation:
            return int(rotation)
    except subprocess.CalledProcessError:
        pass

    return 0
        
if __name__ == '__main__':
    dir = sys.argv[1]
    for root, dirs, files in os.walk(dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov']):
                try:
                    src = os.path.join(root, file)
                    rotation = get_rotation_metadata(src)

                    if rotation != 0:
                        dst = os.path.join(root, file.replace(".MOV", "_.MOV").replace(".mov", "_.mov"))
                        template_ffmpeg.process([
                            "-i",
                            src,
                            "-metadata:s:v:0",
                            "rotate=0",
                            "-y",
                            dst
                        ], "")
                        os.remove(src)
                        os.rename(dst, src)
                except Exception as e:
                    print(f"Failed to process {file}: {e}")
                    pass
    