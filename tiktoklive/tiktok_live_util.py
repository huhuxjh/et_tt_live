import asyncio
import os
import queue
import random
import shutil
import sys
import threading

import soundfile
from pydub import AudioSegment

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
    llm_task.done()


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
        if query_queue.not_empty:
            content_item = query_queue.get()
            await create_tts(content_item, ref_speaker_name)
        elif not live_running:
            break
        await asyncio.sleep(1)
    # 结束协程
    global tts_task
    tts_task.done()


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
    duration = sound.duration_seconds * 1000  # 音频时长（ms）
    return duration


def play_audio():
    print("play_audio")
    # 输出设备
    from sounddevice_wrapper import SOUND_DEVICE_NAME
    device_list = SOUND_DEVICE_NAME
    # 如果配置了设备名字，那么通过name_to_index去转换index，保证设备名唯一
    # device_index = name_to_index(device_name)

    # if urgent_tts_queue.not_empty:
    #     urgent_tts = urgent_tts_queue.get()
    #     # todo:优先插入紧急TTS
    content_item = tts_queue.get()
    wav = content_item.wav
    label = content_item.vid_label
    print(f"end to get tts queue, size:{tts_queue.qsize()}")
    device = device_list[device_index]
    if obs_wrapper:
        drive_obs(wav, label)
    play_wav_on_device(wav=wav, device=device)


def drive_obs(wav, label):
    wav_dur = get_wav_dur(wav)
    print(f"drive_obs:{label},{wav_dur}")
    label_list = ["discount_now", "discount_in_live"]
    obs_wrapper.play(random.choice(label_list))
    # todo: drive the obs
    # 调用播放
    # obs_wrapper.play(label, None)

    # 获取视频列表数组 by label
    # get_play_tag_list()

    # 返回数据格式
    # self.tags[tag].append({
    #     "path": os.path.join(sub_tag_dir, tag),
    #     "width": w,
    #     "height": h,
    #     "duration": video_duration,
    #     "played": False
    # })

    # 获取还剩下多长的播放时长,如果没在播放返回0,0
    # get_play_status


async def prepare(ref_speaker_name):
    print("live mode: prepare")
    t5 = asyncio.create_task(llm_query_task())
    t6 = asyncio.create_task(create_tts_task(ref_speaker_name))
    ret = await asyncio.gather(t5, t6)
    print("live mode: prepare", ret)


async def play_prepare(ref_speaker_name):
    print("live mode: play_prepare")
    # t1 = asyncio.create_task(enter_task())
    # t2 = asyncio.create_task(social_task())
    # t3 = asyncio.create_task(broadcast_task())
    # t4 = asyncio.create_task(chat_task())
    t5 = asyncio.create_task(list_prepare_tts_task())
    ret = await asyncio.gather(t5)
    print("live mode: play_prepare", ret)


async def live(ref_speaker_name):
    print("live mode: live start")
    # t1 = asyncio.create_task(enter_task())
    # t2 = asyncio.create_task(social_task())
    # t3 = asyncio.create_task(broadcast_task())
    # t4 = asyncio.create_task(chat_task())
    global llm_task, tts_task
    llm_task = asyncio.create_task(llm_query_task())
    tts_task = asyncio.create_task(create_tts_task(ref_speaker_name))
    ret = await asyncio.gather(llm_task, tts_task)
    print("live mode: live end", ret)


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
    global live_running
    live_running = True
    print('is_prepare, is_play_prepare=', is_prepare(), ', ', is_play_prepare())
    thread = None
    coroutine = None
    if is_prepare():
        asyncio.run(prepare(ref_speaker_name))
    elif is_play_prepare():
        if obs_port > 0:
            obs_wrapper = OBScriptManager(obs_port, local_video_dir)
            obs_wrapper.start()
        thread = play_wav_cycle()
        coroutine = asyncio.run(play_prepare(ref_speaker_name))
    else:
        if obs_port > 0:
            obs_wrapper = OBScriptManager(obs_port, local_video_dir)
            obs_wrapper.start()
        thread = play_wav_cycle()
        coroutine = asyncio.run(live(ref_speaker_name))
    print('coroutine===================>', coroutine)
    print('thread======================>', thread)


def play_wav_cycle():
    def worker():
        global live_running
        while live_running or not tts_queue.empty():
            try:
                play_audio()
            except soundfile.LibsndfileError as ignore:
                print(ignore)
            time.sleep(0.1)

    thread = threading.Thread(target=worker)
    # 我发现现在跑 mode==2 的时候,thread.daemon=True 会导致它while循环一下子就跳出了,
    # 之前不会可能是因为有其他任务在执行,只剩它自己的话就会有问题了
    # thread.daemon = True
    thread.start()
    return thread
