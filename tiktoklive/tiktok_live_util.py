import asyncio
import os
import queue
import random
import shutil
import sys
import threading

import soundfile
from pydub import AudioSegment
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from obs.Auto_script_source_V3 import *

# 引用工程
sys.path.append(os.path.abspath("E:\\ET_TTS"))
from et_base import timer, yyyymmdd, fix_mci
from sounddevice_wrapper import play_wav_on_device
from et_dirs import resources
from et_dirs import outputs_v2
from remote_config.et_service_util import llm_async
from remote_config.et_service_util import tts_async
from selenium.webdriver.common.by import By
from bean.product import ScriptItem
from bean.obs_item_wrapper import ObsItemWrapper

last_chat_message = ""
last_social_message = ""
last_enter_message = ""

last_enter_message_time = 0
last_social_message_time = 0

social_message_min_period = 60
enter_message_min_period = 60  # 进场欢迎最短间隔，60秒内最多发一个

query_queue = queue.Queue(maxsize=2000)
tts_queue = queue.Queue(maxsize=2000)
urgent_query_queue = queue.Queue(maxsize=10)
urgent_tts_queue = queue.Queue(maxsize=10)

# 最近4个OBS视频不能重复
last_obs_queue = deque(maxlen=4)

# obs_queue = queue.Queue(maxsize=3)
obs_queue = []

obs_wrapper = None

local_video_dir = "D:\\video_normal"

enter_reply_list = [
    'hello~',
    'hi~',
    'welcome~',
]

like_reply_list = [
    'Appreciate the like❤️❤️❤️'
]

share_reply_list = [
    'Appreciate the share❤️❤️❤️'
]

follow_reply_list = [
    'Appreciate the follow'
]


async def list_prepare_tts_task():
    for _, val in enumerate(product_script.item_list):
        wav = os.path.join(outputs_v2, f'{config_id}{os.path.sep}tts_{val.index}_{device_index}.wav')
        if os.path.exists(wav):
            val.wav = wav
            tts_queue.put(val)
    # 结束协程
    global prepare_tts_task
    if prepare_tts_task: prepare_tts_task.cancel()


async def check_comment():
    global last_chat_message
    # 获取普通聊天List
    try:
        chat_message_list = du.find_css_elements('div[data-e2e="chat-message"]')
        # 获取最近的一条chat_message
        chat_message = chat_message_list[-1]
        if chat_message is None:
            return
        # 获取message中的owner_name 和 comment
        owner_name = chat_message.find_element(by=By.CSS_SELECTOR, value='span[data-e2e="message-owner-name"]').text
        comment = chat_message.find_element(by=By.CSS_SELECTOR, value='div.tiktok-1kue6t3-DivComment').text
    except Exception:
        return
    if owner_name + comment != last_chat_message:
        print(f"chat {owner_name} -> {comment}")
        last_chat_message = owner_name + comment
        # todo: 接LLM --> TTS


async def check_social():
    global last_social_message, last_social_message_time

    current_timestamp = time.time()
    period_time = current_timestamp - last_social_message_time - social_message_min_period
    print(f'social_message period_time {period_time}')
    if period_time < 0:
        return
    # 获取互动消息
    try:
        social_message_list = du.find_css_elements('div[data-e2e="social-message"]')
        # 获取最近的一条social_message
        social_message = social_message_list[-1]
        if social_message is None:
            return
        # 获取message中的owner_name 和 comment
        social_owner_name = social_message.find_element(by=By.CSS_SELECTOR,
                                                        value='span[data-e2e="message-owner-name"]').text
        social_text = social_message.find_element(by=By.CSS_SELECTOR,
                                                  value='div[data-e2e="social-message-text"]').get_attribute(
            "textContent")
    except Exception:
        return
    # 分享： "shared the LIVE video"
    # 关注： "followed the host"
    # 点赞： todo
    if social_owner_name + social_text != last_social_message:
        print(f"social {social_owner_name} -> {social_text}")
        last_social_message = social_owner_name + social_text
        last_social_message_time = current_timestamp
        if social_text.__contains__('shared the LIVE video'):
            share_reply = random.choice(share_reply_list)
            await send_message(share_reply)
        if social_text.__contains__('followed the host'):
            follow_reply = random.choice(follow_reply_list)
            await send_message(follow_reply)


async def check_enter():
    global last_enter_message, last_enter_message_time
    current_timestamp = time.time()
    period_time = current_timestamp - last_enter_message_time - enter_message_min_period
    print(f'enter_message period_time {period_time}')
    if period_time < 0:
        return
    try:
        # 获取进场消息
        enter_message_list = du.find_css_elements('div[data-e2e="enter-message"]')
        # 获取最近的一条enter_message
        enter_message = enter_message_list[-1]
        if enter_message is None:
            return
        # 获取message中的owner_name 和 comment
        enter_owner_name = enter_message.find_element(by=By.CSS_SELECTOR,
                                                      value='span[data-e2e="message-owner-name"]').text
    except Exception:
        return
    enter_text = "joined"
    if enter_owner_name != last_enter_message and len(enter_owner_name) > 0:
        print(f"join {enter_owner_name} -> {enter_text}")
        last_enter_message = enter_owner_name
        enter_reply = random.choice(enter_reply_list)
        last_enter_message_time = current_timestamp
        await send_message(f'{enter_reply} {enter_owner_name}')
        # todo: llm and createTTS and put to urgent_queue


async def send_message(content):
    try:
        du.input_value_by_css('div.tiktok-1l5p0r-DivEditor', content)
        await asyncio.sleep(0.5)
        sendButton = du.find_css_element('div.tiktok-1hya0hm-DivPostButton')
        # du.click_by_element(sendButton)
    except Exception:
        return


async def broadcast_task():
    tasks = [asyncio.create_task(run_scene(scene)) for scene in script_scenes]
    await asyncio.gather(*tasks)


async def run_scene(scene):
    """运行单个场景任务"""
    await asyncio.sleep(scene.start_time)
    while True:
        # 计算下一次执行的时间
        print(f"{scene.content}")
        await send_message(scene.content)
        # 当cycle_time<=0 时，只播放一次
        if scene.cycle_time <= 0:
            return
        # 睡眠直到下一个循环周期
        await asyncio.sleep(scene.cycle_time)


async def enter_task():
    while True:
        await check_enter()
        await asyncio.sleep(2)


async def social_task():
    while True:
        await check_social()
        await asyncio.sleep(3)


async def chat_task():
    while True:
        await check_comment()
        await asyncio.sleep(3)


async def llm_query_task():
    global live_running
    while live_running:
        for _, val in enumerate(product_script.item_list):
            await llm_query(val)
        live_running = False
    # 结束协程
    global llm_task
    print('llm_query_task===>', llm_task)
    if llm_task: llm_task.cancel()


async def llm_query(content_item):
    query = f'go to step {content_item.index}'
    context = product_script.context
    sys_inst = product_script.sys_inst
    role_play = product_script.role_play
    keep = content_item.llm_infer
    # with timer('qa-llama_v3'):
    if keep == 1:
        an = content_item.text.replace('\n', ' ')
    else:
        an = await llm_async(query, role_play, context, sys_inst, 3, 1.05)
    new_content_item = ScriptItem(index=content_item.index, text=an, llm_infer=content_item.llm_infer,
                                  tts_type=content_item.tts_type, vid_label=content_item.vid_label)
    query_queue.put(new_content_item)
    print(f"query_queue put size:{query_queue.qsize()}")
    await asyncio.sleep(1)


async def create_tts_task(ref_speaker_name):
    global live_running
    print("create_tts_task")
    while True:
        if not query_queue.empty():
            content_item = query_queue.get()
            await create_tts(content_item, ref_speaker_name)
        elif not live_running:
            break
        await asyncio.sleep(1)
    # 结束协程
    global tts_task
    print('create_tts_task===>', tts_task)
    if tts_task: tts_task.cancel()


async def create_tts(content_item, ref_speaker_name):
    # todo: 配置传入
    # todo: tts 生成的名字，现在的idx仍然可能重复
    print(f"create_tts: {content_item.index}")
    ref_speaker = os.path.join(resources, ref_speaker_name)
    # 参考音频
    ref_audios = [ref_speaker]
    for idx, audio in enumerate(ref_audios):
        name, suffix = os.path.splitext(os.path.basename(audio))
        if suffix != '.wav':
            audio_dir = os.path.dirname(audio)
            audio = fix_mci(audio, output_path=os.path.join(audio_dir, f'{name}.wav'))
            ref_audios[idx] = audio
    # 开始推理
    idx_turn = content_item.index
    an = content_item.text
    print(f'assistant> ', an)
    # 准备模式，把tts保存到固定路径
    if is_prepare():
        out = os.path.join(outputs_v2, f'{config_id}{os.path.sep}tts_{idx_turn}_{device_index}.wav')
    else:  # 非准备模式，把tts保存到当天的路径
        out = os.path.join(outputs_v2, f'{yyyymmdd}_{config_id}{os.path.sep}tts_{idx_turn}_{device_index}.wav')
    # 如果文件夹不存在创建文件夹
    out_dir = os.path.dirname(out)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    with timer('tts-local'):
        ref_name, _ = os.path.splitext(os.path.basename(random.choice(ref_audios)))
        output_name, _ = os.path.splitext(os.path.basename(out))
        wav = await tts_async(an, ref_name, output_name, content_item.tts_type)
        wav = wav.replace('"', '')
        # 复制到本地
        shutil.copy(wav, out)
        content_item.wav = out
        # wav 入队
        tts_queue.put(content_item)


def get_wav_dur(wav):
    sound = AudioSegment.from_wav(wav)
    duration = sound.duration_seconds  # 音频时长（s）
    return duration


def play_audio(callback):
    print("play_audio")
    # 输出设备
    from sounddevice_wrapper import SOUND_DEVICE_NAME
    device_list = SOUND_DEVICE_NAME
    # 如果配置了设备名字，那么通过name_to_index去转换index，保证设备名唯一
    # device_index = name_to_index(device_name)

    # if not urgent_tts_queue.empty():
    #     urgent_tts = urgent_tts_queue.get()
    #     # todo:优先插入紧急TTS
    content_item = tts_queue.get()
    wav = content_item.wav
    label = content_item.vid_label
    print(f"end to get tts queue, size:{tts_queue.qsize()}")
    device = device_list[device_index]
    if obs_wrapper:
        drive_video(wav, label)
    if obs_wrapper:
        print(str(time.time()) + f"play_audio  -->  {wav}")
        obs_wrapper.play_audio(wav=wav, callback=callback)
    else:
        play_wav_on_device(wav=wav, device=device)
        callback()


def play_video(callback):
    global obs_queue
    print(f"try play_obs, obs_queue:{len(obs_queue)}")
    if len(obs_queue) == 0:
        return False
    obs_item_wrapper = obs_queue[0]
    if len(obs_queue) > 1:
        obs_queue = obs_queue[1:]
    print(f"play_obs obs_item_wrapper:{obs_item_wrapper.obs_item['duration']}")
    if obs_wrapper:
        print(str(time.time()) + "=========== play " + obs_item_wrapper.obs_item["path"])
        return obs_wrapper.play_video(obs_item_wrapper.label, obs_item_wrapper.obs_item["path"], callback=callback)
    return False


def in_recent_play_queue(path):
    for element in last_obs_queue:
        if element == path:
            return True
    return False


# 找可用的，与wav时长最接近的obs
def get_suitable_obs(wav_dur, obs_list):
    diff_time = 10000
    suitable_item = None
    for item in obs_list:
        temp_diff = abs(item["duration"] - wav_dur)
        if temp_diff < diff_time:
            diff_time = temp_diff
            suitable_item = item
    return suitable_item


def drive_video(wav, label):
    wav_dur = get_wav_dur(wav)
    print(f"drive_video:{label}, {wav_dur}")

    play_list = obs_wrapper.get_play_tag_list(label)
    # 把最近播放过的（最近4个）排除掉，得出一个当前可用的list:
    available_list = []
    for item in play_list:
        path = item["path"]
        if not in_recent_play_queue(path):
            available_list.append(item)

    global obs_queue
    cur, obs_dur = obs_wrapper.get_video_status()
    # Video还要播放多久
    remain_time = obs_dur - cur
    if obs_dur > 0 and remain_time > 0:
        if remain_time < 2:  # 剩余小于2秒直接塞
            suitable_item = get_suitable_obs(wav_dur=wav_dur, obs_list=available_list)
            if suitable_item:
                print("put obs_queue: remain_time < 2")
                obs_queue.append(ObsItemWrapper(obs_item=suitable_item, label=label))
        elif remain_time > wav_dur:  # obs剩余的播放时长比当前要播放的TTS还长的话，就什么都不做。
            print("remain_time > wav_dur ==>do nothing ")
        else:  # 基于当前TTS下次超出的时间去找一个合适的视频
            fix_time = wav_dur - remain_time
            suitable_item = get_suitable_obs(wav_dur=fix_time, obs_list=available_list)
            if suitable_item:
                obs_queue.append(ObsItemWrapper(obs_item=suitable_item, label=label))
                print("put obs_queue: obs is_playing")

    else:
        # 当前没有在播放Video:
        suitable_item = get_suitable_obs(wav_dur=wav_dur, obs_list=available_list)
        if suitable_item:
            obs_queue.append(ObsItemWrapper(obs_item=suitable_item, label=label))
            print("put obs_queue: obs is not playing")
        else:
            print("no suitable video, use random video")
            obs_queue.append(ObsItemWrapper(obs_item=random.choice(play_list), label=label))



async def prepare(ref_speaker_name):
    print("live mode: prepare")
    global llm_task, tts_task
    llm_task = asyncio.create_task(llm_query_task())
    tts_task = asyncio.create_task(create_tts_task(ref_speaker_name))
    try:
        await asyncio.gather(llm_task, tts_task)
    except asyncio.CancelledError:
        print("live mode: prepare")


async def play_prepare(ref_speaker_name):
    print("live mode: play_prepare")
    # t1 = asyncio.create_task(enter_task())
    # t2 = asyncio.create_task(social_task())
    # t3 = asyncio.create_task(broadcast_task())
    # t4 = asyncio.create_task(chat_task())
    global prepare_tts_task
    prepare_tts_task = asyncio.create_task(list_prepare_tts_task())
    try:
        await asyncio.gather(prepare_tts_task)
    except asyncio.CancelledError:
        print("live mode: play_prepare")


async def live(ref_speaker_name):
    print("live mode: live start")
    # t1 = asyncio.create_task(enter_task())
    # t2 = asyncio.create_task(social_task())
    # t3 = asyncio.create_task(broadcast_task())
    # t4 = asyncio.create_task(chat_task())
    global llm_task, tts_task
    llm_task = asyncio.create_task(llm_query_task())
    tts_task = asyncio.create_task(create_tts_task(ref_speaker_name))
    try:
        await asyncio.gather(llm_task, tts_task)
    except asyncio.CancelledError:
        print("live mode: live end")


def is_prepare():
    return live_mode == "1"


def is_play_prepare():
    return live_mode == "2"


def startClient(browserId, scenes, product, ref_speaker_name, device_id, obs_port, mode, configId):
    global obs_wrapper
    global du, script_scenes, product_script, device_index, live_mode, config_id
    script_scenes = scenes
    product_script = product
    device_index = device_id
    live_mode = mode
    config_id = configId
    # driver,_ = chrome_utils.get_driver(browserId)
    # if driver:
    #     du = driver_utils.DriverUtils(driver)
    #     #启动协程
    #     asyncio.run(main())
    global live_running, force_stop
    live_running = True
    force_stop = False
    print('is_prepare, is_play_prepare=', is_prepare(), ', ', is_play_prepare())
    audio_thread = None
    video_thread = None
    if is_prepare():
        asyncio.run(prepare(ref_speaker_name))
    elif is_play_prepare():
        if obs_port > 0:
            obs_wrapper = OBScriptManager(obs_port, local_video_dir, True)
            obs_wrapper.start()
            # video_thread = play_video_cycle()
        audio_thread = play_wav_cycle()
        asyncio.run(play_prepare(ref_speaker_name))
    else:
        if obs_port > 0:
            obs_wrapper = OBScriptManager(obs_port, local_video_dir, True)
            obs_wrapper.start()
            # video_thread = play_video_cycle()
        audio_thread = play_wav_cycle()
        asyncio.run(live(ref_speaker_name))
    print('thread force stop', audio_thread)
    if audio_thread and audio_thread.is_alive():
        force_stop = True


def play_wav_cycle():
    def worker():
        global live_running, force_stop
        while live_running or not force_stop:
            try:
                a1, a2 = obs_wrapper.get_audio_status()
                if a2 == 0 or (a2 - a1) == 0:
                    play_audio(None)

                v1, v2 = obs_wrapper.get_video_status()
                if v2 == 0 or (v2 - v1) == 0:
                    play_video(None)
            except soundfile.LibsndfileError as ignore:
                print(ignore)
            time.sleep(0.1)

    thread = threading.Thread(target=worker)
    thread.start()
    return thread

#
# end = False
#
#
# def play_wav_cycle():
#     def worker():
#         global live_running, force_stop
#         while live_running or not force_stop:
#             try:
#                 global end
#                 end = False
#
#                 def complete():
#                     global end
#                     end = True
#
#                 play_audio(complete)
#                 while not end:
#                     time.sleep(1)
#             except soundfile.LibsndfileError as ignore:
#                 print(ignore)
#             time.sleep(0.5)
#
#     thread = threading.Thread(target=worker)
#     thread.start()
#     return thread
#

# video_end = False
#
#
# def play_video_cycle():
#     def worker():
#         global live_running, force_stop
#         while live_running or not force_stop:
#             try:
#                 global video_end
#                 video_end = False
#
#                 def video_complete():
#                     print("receive video_complete")
#                     global video_end
#                     video_end = True
#                 if play_video(video_complete):
#                     while not video_end:
#                         time.sleep(1)
#             except Exception as ignore:
#                 print(ignore)
#             time.sleep(0.5)
#
#     thread = threading.Thread(target=worker)
#     thread.start()
#     return thread
# from template_generator import ffmpeg as template_ffmpeg
# for root, dirs, files in os.walk("D:\\video_normal"):
#     for file in files:
#         # 检查文件扩展名是否匹配
#         if any(file.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov']):
#             src = os.path.join(root, file)
#             dst = os.path.join(root, file.replace(".MOV", "_.MOV").replace(".mov", "_.mov"))
#             template_ffmpeg.process([
#                 "-i",
#                 src,
#                 "-metadata:s:v:0",
#                 "rotate=0",
#                 "-y",
#                 dst
#             ], "")
#             os.remove(src)
#             os.rename(dst, src)
