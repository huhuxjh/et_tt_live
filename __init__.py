import os
import sys


base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir in sys.path:
    sys.path.remove(base_dir)
sys.path.insert(0, base_dir)
# 引用工程
sys.path.append(os.path.abspath("E:\\ET_TTS"))
