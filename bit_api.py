import datetime
import time

import requests
from logger import Logger

request = requests.session()
url = "http://127.0.0.1:54345"
log = Logger()

def openBrowser(id):  # 打开窗口
    headers = {'id': id}
    res = request.post(f"{url}/browser/open", json=headers).json()
    log.logger.info(f'打开browser:{res}')
    return res


def closeBrowser(id):  # 关闭窗口
    headers = {'id': f'{id}'}
    res = request.post(f"{url}/browser/close", json=headers).json()
    log.logger.info(f'关闭browser:{res}')
    time.sleep(3)


def get_all_browser():
    headers = {'page': 0, 'pageSize': 10}
    res = request.post(f"{url}/browser/list", json=headers).json()
    # log.logger.info(f'所有browser:{res}')
    return res['data']['list']


def get_id_by_name(user_name):
    browser_list = get_all_browser()
    for b in browser_list:
        if user_name == b['remark']:
            return b['id']
    return ''


if __name__ == '__main__':
    # openBrowser('2600696508514024b52982124919431f')
    print(get_all_browser())
    # print(get_id_by_name('edenworm@outlook.com'))
