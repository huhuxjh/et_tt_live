import asyncio
import os
import random
import shutil
import sys
import threading
import time

import chrome_utils
import driver_utils
from tiktoklive import promopt_util
import soundfile
from pydub import AudioSegment
from collections import deque
from remote_config import lark_util


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
from bean.obs_item_wrapper import ObsItemWrapper

last_chat_message = ""
last_social_message = ""
last_enter_message = ""

last_enter_message_time = 0
last_social_message_time = 0

social_message_min_period = 50
enter_message_min_period = 50

last_play_effect_time = 0

query_queue = queue.Queue()
tts_queue = queue.Queue()

# 公屏队列
text_queue = queue.Queue()

urgent_query_queue = queue.Queue(maxsize=10)
urgent_tts_queue = queue.Queue(maxsize=10)

# 最近播放的OBS视频
last_obs_queue = deque()

obs_queue = []

obs_wrapper = None

local_video_dir = "D:\\video_res"

welcome_list = ["welcome", "hi", "hello, welcome to the live stream"]

followed_list = ["Appreciate the followed","Appreciate the followed, thank you very much"]

shared_list = ["Appreciate the shared", "Thank you for sharing the live stream"]




async def list_prepare_tts_task():
    for _, val in enumerate(product_script.item_list):
        # wav = os.path.join(outputs_v2, f'{config_id}{os.path.sep}tts_{val.index}_{device_index}.wav')
        wav = val.wav
        print(f"product_script wav:{wav}")
        if os.path.exists(wav):
            val.wav = wav
            tts_queue.put(val)


async def check_comment():
    global last_chat_message, script_config
    # 获取普通聊天List
    try:
        print(f"check_comment")

        chat_message_list = du.find_css_elements('div[data-e2e="chat-message"]')
        # 获取最近的一条chat_message
        chat_message = chat_message_list[-1]
        print(f"check_comment chat_message:{chat_message}")

        if chat_message is None:
            return
        # 获取message中的owner_name 和 comment
        owner_name = chat_message.find_element(by=By.CSS_SELECTOR, value='span[data-e2e="message-owner-name"]').text
        comment = chat_message.find_element(by=By.CSS_SELECTOR, value='div.css-1kue6t3-DivComment').text
        print(f" check_comment live room comment:{comment}")
    except Exception as e:
        print(f"check_comment exception:{e}")

        return
    if owner_name + comment != last_chat_message:
        print(f"chat {owner_name} -> {comment}")
        last_chat_message = owner_name + comment
        await llm_query_for_active(promopt_util.chat_with(owner_name, comment))


async def check_social():
    global last_social_message, last_social_message_time

    current_timestamp = time.time()
    # 开播20秒后才开始
    if last_social_message_time == 0:
        last_social_message_time = current_timestamp - 20
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
    # 关注： "followed the host"result
    # 点赞： todo
    if social_owner_name + social_text != last_social_message:
        print(f"social {social_owner_name} -> {social_text}")
        last_social_message = social_owner_name + social_text
        last_social_message_time = current_timestamp
        if social_text.__contains__('shared the LIVE video'):
            index = random.randrange(0, 1)
            if index == 0:
                await create_tts_for_active(f"{random.choice(shared_list)}, {social_owner_name}")
            else:
                text_queue.put(f"{random.choice(shared_list)}, {social_owner_name}")

        if social_text.__contains__('followed the host'):
            index = random.randrange(0, 1)
            if index == 0:
                await create_tts_for_active(f"{random.choice(followed_list)}, {social_owner_name}")
            else:
                text_queue.put(f"{random.choice(followed_list)}, {social_owner_name}")


async def check_enter():
    global last_enter_message, last_enter_message_time
    current_timestamp = time.time()
    # 开场10秒后才开始
    if last_enter_message_time == 0:
        last_enter_message_time = current_timestamp - 10
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
    print(f'enter_message enter_owner_name {enter_owner_name}, last_enter_message {last_enter_message}')
    if enter_owner_name != last_enter_message and len(enter_owner_name) > 0:
        print(f"join {enter_owner_name} -> {enter_text}")
        last_enter_message = enter_owner_name
        last_enter_message_time = current_timestamp
        index = random.randrange(0,1)
        if index == 0:
            await create_tts_for_active(f"{random.choice(welcome_list)}, {enter_owner_name}")
        else:
            text_queue.put(f"{random.choice(welcome_list)}, {enter_owner_name}")


# 互动的llm查询
async def llm_query_for_active(query):
    context = product_script.context
    # 在互动过程中，query就是指令
    # 在脚本过程中，query只是内容，sys_inst是指令
    sys_inst = product_script.sys_inst
    role_play = product_script.role_play
    max_num_sentence = 8
    with timer('qa-llama_v3'):
        an = await llm_async(query, role_play, context, sys_inst, max_num_sentence, 1.05)
    print(f"llm_query_for_active an:{an}")
    await create_tts_for_active(an)

async def create_tts_for_active(content):
    ref_speaker = os.path.join(resources, script_config.ref_speaker)
    # 参考音频
    ref_audios = [ref_speaker]
    for idx, audio in enumerate(ref_audios):
        name, suffix = os.path.splitext(os.path.basename(audio))
        if suffix != '.wav':
            audio_dir = os.path.dirname(audio)
            audio = fix_mci(audio, output_path=os.path.join(audio_dir, f'{name}.wav'))
            ref_audios[idx] = audio

    out = os.path.join(outputs_v2, f'{yyyymmdd}_{config_id}{os.path.sep}tts_{time.time()}.wav')

    out_dir = os.path.dirname(out)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    with timer('tts-local'):
        ref_name, _ = os.path.splitext(os.path.basename(random.choice(ref_audios)))
        output_name, _ = os.path.splitext(os.path.basename(out))
        wav = await tts_async(content, ref_name, output_name, "ov_v2")
        wav = wav.replace('"', '')
        # 复制到本地
        shutil.copy(wav, out)
        # wav 入队
        urgent_tts_queue.put(out)


async def send_message(content):
    try:
        du.input_value_by_css('div[data-e2e="comment-text"]', content)
        await asyncio.sleep(0.5)
        sendButton = du.find_css_element('div[data-e2e="comment-post"]')
        du.click_by_element(sendButton)
    except Exception:
        print("send_message error")
        return


async def broadcast_task():
    print(f"script_scenes:{len(script_scenes)}")
    tasks = [asyncio.create_task(run_scene(scene)) for scene in script_scenes]
    await asyncio.gather(*tasks)


async def run_scene(scene):
    """运行单个场景任务"""
    print(f"run_scene scene.start_time: {scene.start_time}")

    await asyncio.sleep(scene.start_time)
    while True:
        # 计算下一次执行的时间
        print(f"assistant chat room content: {scene.content}")
        text_queue.put(scene.content)
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

async def send_message_task():
    while True:
        print(f"send_message_task check: text_queue.size ={text_queue.qsize()}")
        if not text_queue.empty():
            message = text_queue.get()
            await send_message(message)
        await asyncio.sleep(1)


async def chat_task():
    while True:
        await check_comment()
        await asyncio.sleep(3)


async def llm_query_task():
    for _, val in enumerate(product_script.item_list):
            await llm_query(val)


async def llm_query(content_item):
    query = content_item.text
    context = product_script.context
    sys_inst = product_script.sys_inst
    role_play = product_script.role_play
    max_num_sentence = 16
    tts_directly = content_item.llm_infer == 0
    with timer('qa-llama_v3'):
        if tts_directly:
            an = query
        else:
            an = await llm_async(query, role_play, context, sys_inst, max_num_sentence, 1.05)
    # 重新打包
    new_content_item = content_item.copy(text=an)
    query_queue.put(new_content_item)
    print(f"query_queue put size:{query_queue.qsize()}")
    await asyncio.sleep(1)


async def create_tts_task():
    global product_script
    print("create_tts_task")
    while True:
        if not query_queue.empty():
            content_item = query_queue.get()
            await create_tts(content_item, product_script)
        await asyncio.sleep(1)


async def create_tts_task_for_preload():
    print("create_tts_task_for_preload")
    global preload_product
    while True:
        if not query_queue.empty():
            content_item = query_queue.get()
            await create_tts(content_item, product=preload_product)
        await asyncio.sleep(1)



async def create_tts(content_item, product):
    global script_round, script_config
    print(f"create_tts: {content_item.index}")
    ref_speaker = os.path.join(resources, script_config.ref_speaker)
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
    out = os.path.join(outputs_v2, f'{config_id}_{script_round}{os.path.sep}tts_{idx_turn}_{device_index}_{script_round}.wav')
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
        # 预生成的TTS不会马上入队，只有在切换脚本的时候，才一次性入队
        if live_run_mode == 0:
            tts_queue.put(content_item)
    # feed back到product_script
    product.update_script_item(content_item)


def get_wav_dur(wav):
    sound = AudioSegment.from_wav(wav)
    duration = sound.duration_seconds  # 音频时长（s）
    return duration


def play_audio(callback):
    print("play_audio")
    global need_switch
    # 输出设备
    from sounddevice_wrapper import SOUND_DEVICE_NAME
    device_list = SOUND_DEVICE_NAME
    # 如果配置了设备名字，那么通过name_to_index去转换index，保证设备名唯一
    # device_index = name_to_index(device_name)
    label = ""
    print(f"urgent_tts_queue, size:{urgent_tts_queue.qsize()}")
    if not urgent_tts_queue.empty():
        wav = urgent_tts_queue.get()
    else:
        content_item = tts_queue.get()
        wav = content_item.wav
        label = content_item.vid_label
        if content_item.index == len(product_script.item_list):
            need_switch = True
    print(f"end to get tts queue, size:{tts_queue.qsize()}, wav:{wav} {time.time()}")
    device = device_list[device_index]
    if obs_wrapper:
        drive_video(wav, label)
    if obs_wrapper:
        print(str(time.time()) + f"play_audio  -->  {wav}")
        obs_wrapper.play_audio(wav=wav, callback=callback)
    else:
        play_wav_on_device(wav=wav, device=device)
        if callback: callback()



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
        play_trans_effect()
        return obs_wrapper.play_video(obs_item_wrapper.label, obs_item_wrapper.obs_item["path"], callback=callback)
    return False


# 转场特效
def play_trans_effect():
    if obs_wrapper:
        index = random.randrange(1, 3)
        if index == 1:
            print(f"play_effect:")
            param = {"duration": random.uniform(3, 4), "scale": random.uniform(1.2, 1.5),
                     "xOffset": random.uniform(0.4, 0.6), "yOffset": random.uniform(0.4, 0.6)}
            obs_wrapper.play_effect(OBS_MEDIA_VIDEO_EFFECT_2, param)
        elif index == 2:
            print("====================  OBS_MEDIA_VIDEO_EFFECT_3")
            param = {"duration": random.uniform(0.5, 1.0),
                     "scale": random.uniform(0.1, 0.1),
                     "xOffset": random.uniform(0.03, 0.06),
                     "yOffset": random.uniform(0.01, 0.03),
                     "freq": random.uniform(2.0, 8.0), }
            obs_wrapper.play_effect(OBS_MEDIA_VIDEO_EFFECT_3, param)


# 随机播
play_effect_period = 10


def play_random_effect():
    print("====================")
    global play_effect_period, last_play_effect_time
    current_time = time.time()
    if obs_wrapper and (current_time - last_play_effect_time) > play_effect_period:
        print("====================  play_effect3")
        param = {"duration": random.uniform(0.5, 1.0),
                 "scale": random.uniform(0.1, 0.1),
                 "xOffset": random.uniform(0.03, 0.06),
                 "yOffset": random.uniform(0.01, 0.03),
                 "freq": random.uniform(2.0, 8.0), }
        obs_wrapper.play_effect(OBS_MEDIA_VIDEO_EFFECT_3, param)
        play_effect_period = random.randrange(8, 10)
        last_play_effect_time = current_time


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


def append_last_obs_queue(obs_item):
    if len(last_obs_queue) >= 6:
        last_obs_queue.popleft()
    last_obs_queue.append(obs_item)


def drive_video(wav, label):
    if len(label) == 0:
        return
    wav_dur = get_wav_dur(wav)
    print(f"drive_video:{label}, {wav_dur}")

    play_list = obs_wrapper.get_play_tag_list(label)
    # 把最近播放过的排除掉，得出一个当前可用的list:
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
                append_last_obs_queue(suitable_item)
        elif remain_time > wav_dur:  # obs剩余的播放时长比当前要播放的TTS还长的话，就什么都不做。
            print("remain_time > wav_dur ==>do nothing ")
        else:  # 基于当前TTS下次超出的时间去找一个合适的视频
            fix_time = wav_dur - remain_time
            suitable_item = get_suitable_obs(wav_dur=fix_time, obs_list=available_list)
            if suitable_item:
                obs_queue.append(ObsItemWrapper(obs_item=suitable_item, label=label))
                append_last_obs_queue(suitable_item)
                print("put obs_queue: obs is_playing")

    else:
        # 当前没有在播放Video:
        suitable_item = get_suitable_obs(wav_dur=wav_dur, obs_list=available_list)
        if suitable_item:
            obs_queue.append(ObsItemWrapper(obs_item=suitable_item, label=label))
            append_last_obs_queue(suitable_item)
            print("put obs_queue: obs is not playing")
        else:
            if len(play_list) > 0:
                print("no suitable video, use random video")
                random_item = random.choice(play_list)
                obs_queue.append(ObsItemWrapper(obs_item=random_item, label=label))
                append_last_obs_queue(random_item)



async def play_prepare():
    print("live mode: play_prepare")
    try:
        if interactive_enable:
            t0 = asyncio.create_task(enter_task())
            t1 = asyncio.create_task(social_task())
            t2 = asyncio.create_task(broadcast_task())
            t3 = asyncio.create_task(chat_task())
            t4 = asyncio.create_task(retrieve_live_script())
            t5 = asyncio.create_task(switch_script())
            t6 = asyncio.create_task(list_prepare_tts_task())
            t7 = asyncio.create_task(create_tts_task_for_preload())
            t8 = asyncio.create_task(send_message_task())
            await asyncio.gather(t0,t1,t2,t3,t4,t5,t6,t7,t8)
        else:
            t4 = asyncio.create_task(retrieve_live_script())
            t5 = asyncio.create_task(switch_script())
            t6 = asyncio.create_task(list_prepare_tts_task())
            t7 = asyncio.create_task(create_tts_task_for_preload())
            await asyncio.gather(t4, t5, t6, t7)
    except asyncio.CancelledError:
        print("live mode: play_prepare")


async def live():
    print("live mode: live start")
    try:
        if interactive_enable:
            enter = asyncio.create_task(enter_task())
            social = asyncio.create_task(social_task())
            broadcast = asyncio.create_task(broadcast_task())
            chat = asyncio.create_task(chat_task())
            llm_task = asyncio.create_task(llm_query_task())
            tts_task = asyncio.create_task(create_tts_task())
            await asyncio.gather(tts_task)
        else:
            llm_task = asyncio.create_task(llm_query_task())
            tts_task = asyncio.create_task(create_tts_task())
            await asyncio.gather(tts_task)
    except asyncio.CancelledError:
        print("live mode: live end")



def start_live(scenes, product, obs_video_port, obs_audio_port, run_mode, c_id, interactive, config):
    global obs_wrapper
    global du, script_scenes, product_script, device_index, config_id, interactive_enable, script_config, script_round, need_switch, live_run_mode
    print(f"scenes:{len(scenes)}")
    script_scenes = scenes
    product_script = product
    device_index = config.sound_device
    config_id = c_id
    interactive_enable = interactive
    script_config = config
    script_round = 0
    live_run_mode = run_mode

    if interactive_enable:
        driver, _ = chrome_utils.get_driver(config.browser_id)
        if driver:
            du = driver_utils.DriverUtils(driver)

    if run_mode == 2:
        if obs_video_port > 0:
            obs_wrapper = OBScriptManager(obs_video_port, obs_audio_port, local_video_dir)
            obs_wrapper.start()
        play_wav_cycle()
        # 开始预生成下一场的脚本和TTS
        asyncio.run(play_prepare())
    else:
        if obs_video_port > 0:
            obs_wrapper = OBScriptManager(obs_video_port, obs_audio_port, local_video_dir)
            obs_wrapper.start()
        play_wav_cycle()
        asyncio.run(live())


def play_wav_cycle():
    def worker():
        while True:
            try:
                if obs_wrapper:
                    a1, a2 = obs_wrapper.get_audio_status()
                    if a2 == 0 or (a2 - a1) == 0:
                        play_audio(None)

                    v1, v2 = obs_wrapper.get_video_status()
                    if v2 == 0 or (v2 - v1) == 0:
                        play_video(None)

                    play_random_effect()

                else:
                    play_audio(None)
            except soundfile.LibsndfileError as ignore:
                print(ignore)
            time.sleep(random.uniform(0.5, 1))

    thread = threading.Thread(target=worker)
    thread.start()
    return thread


need_switch = False
# 该场直播结束，切换下一场脚本
async def switch_script():
    global preload_product, product_script, need_switch
    while True:
        if need_switch:
            # 收到切换脚本的指令后，一分钟之后开始，这里还需要减去最后一句tts的时间，所以等待时间等于（1分钟-最后一句TTS的时间）
            need_switch = False
            await asyncio.sleep(40)
            product_script = preload_product
            print(f"switch_script next tts length:{len(product_script.item_list)}")
            # 把预生成的TTS添加进queue
            for _, val in enumerate(product_script.item_list):
                wav = val.wav
                print(f"product_script wav:{wav}")
                if os.path.exists(wav):
                    val.wav = wav
                    tts_queue.put(val)
            # 继续生成下一场
            await retrieve_live_script()
        await asyncio.sleep(2)


# 生成新的脚本
async def retrieve_live_script():
    global script_config, config_id, preload_product, script_round
    script_round = script_round + 1
    print(f"retrieve_live_script round:{script_round}")

    preload_product = lark_util.retrieve_live_script(config_id=config_id,sheet_id=script_config.product_sheet,src_range=script_config.product_range,seed=script_config.seed,script_round=script_round)
    
    # 把新脚本的item 入队进行llm处理
    for _, val in enumerate(preload_product.item_list):
        await llm_query(val)