import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json


async def post_retry(url, headers, data):
    retry_times = 3  # 设置重试次数
    retry_backoff_factor = 2.0  # 设置重试间隔时间
    session = requests.Session()
    retry = Retry(total=retry_times, backoff_factor=retry_backoff_factor, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session.post(url, headers=headers, json=data)


async def qa_async(query, role_play, context, inst_text, max_num_sentence):
    url = "http://127.0.0.1:9394/llm/tr"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "query": query,
        "role_play": role_play,
        "context": context,
        "inst_text": inst_text,
        "max_num_sentence": max_num_sentence
    }
    response = await post_retry(url, headers, data)
    resp_json = json.loads(response.text)
    return resp_json['text']


async def tts_async(text, ref_name, out_name):
    url = "http://127.0.0.1:9394/tts/tr"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "ref_name": ref_name,
        "out_name": out_name
    }
    response = await post_retry(url, headers, data)
    resp_json = json.loads(response.text)
    return resp_json['path']
