import asyncio
import os
import queue
import random
import shutil
import sys

from pydub import AudioSegment
from bean.product import Config

# 引用工程
sys.path.append(os.path.abspath("E:\\ET_TTS"))
from et_base import timer, yyyymmdd, fix_mci
from et_dirs import resources
from et_dirs import outputs_v2
from remote_config.et_service_util import llm_async
from remote_config.et_service_util import tts_async


query_queue = queue.Queue()
tts_queue = queue.Queue()


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
    global live_running
    print("create_tts_task")
    while True:
        if not query_queue.empty():
            content_item = query_queue.get()
            await create_tts(content_item)
        elif not live_running:
            break
        await asyncio.sleep(1)
    # 结束协程
    global tts_task
    print('create_tts_task===>', tts_task)
    if tts_task: tts_task.cancel()


async def create_tts(content_item):
    print(f"create_tts: {content_item.index}")
    global ref_speaker_name
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
    out = os.path.join(outputs_v2, f'{config_id}{os.path.sep}tts_{idx_turn}_{device_index}.wav')

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
    # feed back到product_script
    product_script.update_script_item(content_item)


async def prepare():
    print("live mode: prepare")
    global llm_task, tts_task, live_running
    llm_task = asyncio.create_task(llm_query_task())
    tts_task = asyncio.create_task(create_tts_task())
    try:
        live_running = True
        await asyncio.gather(llm_task, tts_task)
    except asyncio.CancelledError:
        print("live mode: prepare")


def start_prepare(product, configId, config):
    global product_script, device_index, config_id, ref_speaker_name
    product_script = product
    device_index = config.sound_device
    config_id = configId
    ref_speaker_name = config.ref_speaker

    asyncio.run(prepare())


