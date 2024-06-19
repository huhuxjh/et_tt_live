import os.path
import shutil

import lark_oapi as lark
import json
import requests

from bean.product import Config, Script, ScriptItem, Template, TemplateItem
from bean.scene import Scene

app_id = 'cli_a6c746e54a39d013'
app_secret = 'Qs2g6mBytqhN32CVUE1xKhxgR2iigHdi'
spreadsheet_token = 'ECj6s8B5YhIm98tboqJc1hienVe'
tenant_access_token = ''


# SDK 使用说明: https://github.com/larksuite/oapi-sdk-python#readme

def request_tenant_token():
    global tenant_access_token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = json.loads(response.text)

        tenant_access_token = response_data["tenant_access_token"]
        code = response_data["code"]
        expire = response_data["expire"]
        msg = response_data["msg"]

        print(f"tenant_access_token: {tenant_access_token}")
        print(f"code: {code}")
        print(f"expire: {expire}")
        print(f"msg: {msg}")
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)


def query_sheet_range(sheet_id, range_value):
    # 先处理token
    if tenant_access_token == '':
        request_tenant_token()

    # 请求逻辑
    client = lark.Client.builder() \
        .enable_set_token(True) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    read_req: lark.BaseRequest = lark.BaseRequest.builder() \
        .http_method(lark.HttpMethod.GET) \
        .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!{range_value}") \
        .token_types({lark.AccessTokenType.TENANT}) \
        .build()

    # option = lark.RequestOption.builder().user_access_token(user_access_token).build()
    option = lark.RequestOption.builder().tenant_access_token(tenant_access_token).build()
    read_resp = client.request(read_req, option)

    read_data = json.loads(str(read_resp.raw.content, lark.UTF_8)).get("data")
    values = read_data.get("valueRange").get("values")
    return values
    # if not read_resp.success():
    #     lark.logger.error(
    #         f"client.im.v1.message.create failed, "
    #         f"code: {read_resp.code}, "
    #         f"msg: {read_resp.msg}, "
    #         f"log_id: {read_resp.get_log_id()}")
    #     return read_resp


def retrieve_config(sheet_id, src_range):
    data_sheet = query_sheet_range(sheet_id, src_range)
    # 获取直播间名字
    room_name = data_sheet[1][0]
    # 获取指纹浏览器ID
    browser_id = data_sheet[2][0]
    # 获取主播商品介绍sheetId
    product_sheet = data_sheet[3][0]
    # 获取主播商品介绍sheet_range
    product_range = data_sheet[4][0]
    # 获取助播公屏配置sheetId
    assist_sheet = data_sheet[5][0]
    # 获取助播公屏配置sheet_range
    assist_range = data_sheet[6][0]
    # 获取主播音色名字
    ref_speaker = data_sheet[7][0]
    # ref_speaker_name = 'man_role0_ref'
    # 获取播放设备id
    sound_device = data_sheet[8][0]
    # device_id = 1
    seed = data_sheet[9][0]
    # seed = 5
    return Config(
        room_name=room_name,
        browser_id=browser_id,
        product_sheet=product_sheet,
        product_range=product_range,
        assist_sheet=assist_sheet,
        assist_range=assist_range,
        ref_speaker=ref_speaker,
        sound_device=sound_device,
        seed=seed,
    )


def query_assist_script(sheet_id, src_range):
    datas = query_sheet_range(sheet_id, src_range)
    scenes = []
    for data in datas:
        start_time, cycle_time, content = data
        scene = Scene(start_time, cycle_time, content)
        scenes.append(scene)
    return scenes


def obtain_safety(text, skip_rep=False):
    if isinstance(text, list):
        text = ''.join([item['text'] for item in text])
    if isinstance(text, str) and not skip_rep:
        text = text.replace('\n', '')
    return text


def query_product_template(sheet_id, src_range, seed) -> Template:
    datas = query_sheet_range(sheet_id, src_range)
    role_play = obtain_safety(datas.pop(0)[1])
    product_info = obtain_safety(datas.pop(0)[1], True)
    sys_inst = obtain_safety(datas.pop(0)[1])
    item_list = []
    for idx, val in enumerate(datas):
        template_tag = obtain_safety(val[0])
        text = obtain_safety(val[1])
        keep_ratio = obtain_safety(val[2])
        tts_type = obtain_safety(val[3])
        vid_label = obtain_safety(val[4])
        template_item = TemplateItem(template_tag=template_tag, text=text,
                                     keep_ratio=keep_ratio, tts_type=tts_type, vid_label=vid_label)
        item_list.append(template_item)
    # 模板脚本分组
    item_group: dict[str, list] = {}
    for item in item_list:
        if item.template_tag in item_group:
            item_group[item.template_tag].append(item)
        else:
            item_group[item.template_tag] = [item]
    # 生成模板实例
    template = Template(context=product_info, sys_inst=sys_inst, role_play=role_play,
                        item_group=item_group, seed=seed)
    return template


def product_product_scrip(template: Template) -> Script:
    script_items = template.produce_script_config()
    # script_items = template.produce_script_all()
    product = Script(context=template.context, sys_inst=template.sys_inst, role_play=template.role_play,
                     item_list=script_items)
    return product


def retrieve_script(config_id, sheet_id, src_range, seed=5, reproduce=False):
    """
    reproduce: True强制删除缓存, False使用缓存
    """
    from bean.product import Script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(base_dir, f'script_{config_id}')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    script_path = os.path.join(base_dir, f'script.json')
    if not reproduce and os.path.exists(script_path):
        product = Script.from_file(script_path)
        # todo: 增加validation
    else:
        # 删除缓存
        if reproduce:
            shutil.rmtree(base_dir)
            os.makedirs(base_dir)
        # 重新生成
        template = query_product_template(sheet_id, src_range, seed)
        product = product_product_scrip(template)
        product.to_file(script_path)
    # 返回结果
    return product


# 直播中动态生成脚本
def retrieve_live_script(config_id, sheet_id, src_range, seed=5, script_round=1):
    # 定义脚本资源文件夹
    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(base_dir, f'script_{config_id}_{script_round}')
    if os.path.exists(base_dir):
        # 删除缓存
        shutil.rmtree(base_dir)
    os.makedirs(base_dir)
    script_path = os.path.join(base_dir, f'script.json')
    template = query_product_template(sheet_id, src_range, seed)
    product = product_product_scrip(template)
    product.to_file(script_path)
    return product

if __name__ == "__main__":
    # query_assist_script()
    pass
