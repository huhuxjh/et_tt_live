import lark_oapi as lark
import json
import requests

from bean.product import Script, ScriptItem, Template, TemplateItem
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


def query_range(sheet_id, range_value):
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


def query_assist_script(sheet_id, src_range):
    datas = query_range(sheet_id, src_range)
    scenes = []
    for data in datas:
        start_time, cycle_time, content = data
        scene = Scene(start_time, cycle_time, content)
        scenes.append(scene)
    return scenes


def to_text_safety(text):
    if isinstance(text, list):
        text = ''.join([item['text'] for item in text])
    return text


def query_product_template(sheet_id, src_range) -> Template:
    datas = query_range(sheet_id, src_range)
    role_play = datas.pop(0)[1]
    product_info = datas.pop(0)[1]
    sys_inst = datas.pop(0)[1]
    item_list = []
    for idx, val in enumerate(datas):
        template_tag = to_text_safety(val[0])
        text = to_text_safety(val[1])
        llm_infer = to_text_safety(val[2])
        tts_type = to_text_safety(val[3])
        vid_label = to_text_safety(val[4])
        template_item = TemplateItem(template_tag=template_tag, text=text,
                                     llm_infer=llm_infer, tts_type=tts_type, vid_label=vid_label)
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
                        item_group=item_group)
    return template


def product_product_scrip(template: Template) -> Script:
    script_items = template.produce_script()
    product = Script(context=template.context, sys_inst=template.sys_inst, role_play=template.role_play,
                     item_list=script_items)
    return product


if __name__ == "__main__":
    # query_assist_script()
    pass
