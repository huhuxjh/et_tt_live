import asyncio
import os
import queue
import random
import sys
import threading
import time

# 引用工程
sys.path.append(os.path.abspath("E:\\ET_TTS"))
from et_base import timer, yyyymmdd, fix_mci
from sounddevice_wrapper import play_wav_on_device
from et_dirs import resources
from et_dirs import outputs_v2
from remote_config.et_service_util import llm_async
from remote_config.et_service_util import tts_async
from selenium.webdriver.common.by import By
from bean.product import ContentItem

last_chat_message = ""
last_social_message = ""
last_enter_message = ""

last_enter_message_time = 0
last_social_message_time = 0

social_message_min_period = 60
enter_message_min_period = 60  # 进场欢迎最短间隔，60秒内最多发一个

query_queue = queue.Queue(maxsize=30)
tts_queue = queue.Queue(maxsize=30)

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
    while True:
        for _,val in enumerate(product_script.contentList):
            await llm_query(val)


async def llm_query(contentItem):
    query = f'go to step {contentItem.index}'
    context = product_script.context
    sys_inst = product_script.sys_inst
    role_play = product_script.role_play
    keep = contentItem.keep
    # with timer('qa-llama_v3'):
    if keep == 1:
        an = contentItem.text
    else:
        an = await llm_async(query, role_play, context, sys_inst, 3, 1.05)
    new_contentItem = ContentItem(index= contentItem.index, text= an, keep=contentItem.keep, spc_type= contentItem.spc_type, label= contentItem.label)
    print(f"query:{query},\ncontext:{context}, \nsys_inst:{sys_inst}, \nrole_play:{role_play}, \nkeep:{keep}")
    print(f"query put size：{query_queue.qsize()}")
    query_queue.put(new_contentItem, block=True)
    print(f"query after put size：{query_queue.qsize()}")
    await asyncio.sleep(1)


async def create_tts_task(ref_speaker_name):
    print("create_tts_task")
    while True:
            if query_queue.not_empty:
                contentItem = query_queue.get()
                await create_tts(contentItem, ref_speaker_name)
            await asyncio.sleep(1)


async def create_tts(contentItem, ref_speaker_name):
    # todo: 配置传入
    # todo: tts 生成的名字，现在的idx仍然可能重复
    print(f"create_tts: {contentItem.index}")
    ref_speaker = os.path.join(resources, ref_speaker_name)
    # 参考音频
    ref_audios = [ref_speaker]
    for idx, audio in enumerate(ref_audios):
        name, suffix = os.path.splitext(os.path.basename(audio))
        if suffix != '.wav':
            audio_dir = os.path.dirname(audio)
            audio = fix_mci(audio, output_path=os.path.join(audio_dir, f'{name}.wav'))
            ref_audios[idx] = audio
    emo_list = ['default', 'excited', 'cheerful']
    # 开始推理
    idx_turn = contentItem.index
    an = contentItem.text
    select_emo = random.choice(emo_list)
    print(f'assistant>({select_emo}) ', an)
    # todo: tts转换（名字要与client绑定，要不会相互覆盖）
    out = os.path.join(outputs_v2, f'{yyyymmdd}{os.path.sep}tts_{idx_turn}_{device_index}.wav')
    with timer('tts-local'):
        ref_name, _ = os.path.splitext(os.path.basename(random.choice(ref_audios)))
        output_name, _ = os.path.splitext(os.path.basename(out))
        wav = await tts_async(an, ref_name, output_name, contentItem.spc_type)
        wav = wav.replace('"', '')
        tts_queue.put(wav, block=True)


def play_audio():
    # todo:
    print("play_audio")
    # 输出设备
    from sounddevice_wrapper import SOUND_DEVICE_NAME
    device_list = SOUND_DEVICE_NAME
    # 如果配置了设备名字，那么通过name_to_index去转换index，保证设备名唯一
    # device_index = name_to_index(device_name)
    print(f"start to get tts queue, size:{tts_queue.qsize()}")
    # if tts_queue.empty():
    #     return
    wav = tts_queue.get()
    print(f"end to get tts queue, size:{tts_queue.qsize()}")
    device = device_list[device_index]
    play_wav_on_device(wav=wav, device=device)


async def main(ref_speaker_name):
    # t1 = asyncio.create_task(enter_task())
    # t2 = asyncio.create_task(social_task())
    # t3 = asyncio.create_task(broadcast_task())
    # t4 = asyncio.create_task(chat_task())
    t5 = asyncio.create_task(llm_query_task())
    t6 = asyncio.create_task(create_tts_task(ref_speaker_name))

    await asyncio.gather(t5, t6)


def startClient(browserId, scenes, product, ref_speaker_name, device_id, obs_port):
    global du, script_scenes, product_script, device_index
    script_scenes = scenes
    product_script = product
    device_index = device_id
    # driver,_ = chrome_utils.get_driver(browserId)
    # if driver:
    #     du = driver_utils.DriverUtils(driver)
    #     #启动协程
    #     asyncio.run(main())
    obs_instance(obs_port)
    play_wav_cycle()
    asyncio.run(main(ref_speaker_name))


def play_wav_cycle():
    def worker():
        while True:
            play_audio()
            time.sleep(0.1)

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()

from obs.Auto_script_source_V2 import *
def obs_instance(obs_port):
    def obs_loop():
        print(f"================================ !!!")
        scriptMgr = OBScriptManager(obs_port)
        scriptMgr.start()
        layers = []
        for n in range(1, 37):
            layers.append(f"product_{n}")
        selected = set()
        def get_random_layer(lll, selected):
            if len(selected) == len(lll):
                selected.clear()
            while True:
                random_layer = random.choice(lll)
                if random_layer not in selected:
                    selected.add(random_layer)
                    return random_layer
        print(f"================================ obs start {obs_port} !!!")
        while True:
            scriptMgr.set_current_layer_queue(get_random_layer(layers, selected))
            if keyboard.is_pressed('q'):
                print("Exiting the OBScriptManager work, Disconnnect from obs !!!!!!!.")
                scriptMgr.stop()
                break
            time.sleep(random.randint(10, 40))

    print("================================ obs start")
    thread = threading.Thread(target=obs_loop)
    thread.daemon = True
    thread.start()

