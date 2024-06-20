import re
import uuid

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json

HOST = 'http://127.0.0.1:9394'
_ET_UUID_ = uuid.uuid1().hex


async def post_retry(url, headers, data):
    retry_times = 3  # 设置重试次数
    retry_backoff_factor = 2.0  # 设置重试间隔时间
    status_force_list = [400, 401, 403, 404, 500, 502, 503, 504]
    session = requests.Session()
    retry = Retry(total=retry_times, backoff_factor=retry_backoff_factor, status_forcelist=status_force_list)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session.post(url, headers=headers, json=data)


async def ver_async():
    """
    返回JSON格式：
    {
      "llm": {
        "llama_v3": true,
        "glm_4": false
      },
      "tts": [
        "ov_v2_English",
        "chat_tts"
      ]
    }
    """
    url = f"{HOST}/llm/tts/ver"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.status_code == 200


async def llm_async(query, role_play, context, inst_text, max_num_sentence, repetition_penalty, language="english"):
    url = f"{HOST}/llm/tr"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "et_uuid": _ET_UUID_,
        "language": language,
        "use_history": False,   # 必须false，要不词频越来越低，到最后胡言乱语
        "query": query,
        "role_play": role_play,
        "context": context,
        "inst_text": inst_text,
        "spc_type": 'llm_llama',      # 可以指定llm大模型类型(llm_llama, llm_glm)，不过每次切换都需要卸载/加载，尽量不要切换
        "max_num_sentence": max_num_sentence,
        "repetition_penalty": repetition_penalty
    }
    response = await post_retry(url, headers, data)
    resp_json = json.loads(response.text)
    resp_text = resp_json['text']
    # 只匹配返回括号包含的内容
    matches = re.findall(r'{(.*?)}', resp_text)
    text = matches[0] if matches else resp_text
    # 结果处理
    text = re.sub(r'^Here(.*)revised(.*):', '', text)
    text = re.sub(r'^Revised(.*):', '', text)
    text = text.strip('"')
    return text


async def tts_async(text, ref_name, out_name, spc_type, language="english"):
    url = f"{HOST}/tts/tr"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    # "spc_type": "ov_v2"
    # "ref_name": ref_name      # 指定音色
    # 以下是chatTTS参数
    # "spc_type": "chat_tts"
    # "manual_seed": 0       # 指定音色: 414女，410男
    # "skip_refine_text": False # True表示自行插入语气
    data = {
        "et_uuid": _ET_UUID_,
        "language": language,
        "text": text,
        "out_name": out_name,
        "spc_type": spc_type,
        "ref_name": ref_name,
        "manual_seed": 8,       # 1~22是预设音色
        "refine_prompt": "[oral_2][laugh_0][break_4]",
        "infer_prompt": "[speed_4]",
        "skip_refine_text": False
    }
    response = await post_retry(url, headers, data)
    resp_json = json.loads(response.text)
    return resp_json['path']
