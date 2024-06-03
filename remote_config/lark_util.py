import lark_oapi as lark
import json
import requests
from lark_oapi.api.sheets.v3 import *
from lark_oapi.api.authen.v1 import *

from bean.product import Product
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


def query_product_script(sheet_id, src_range):
    datas = query_range(sheet_id, src_range)
    contentList = []
    for data in datas:
        content = data[0]
        contentList.append(content)
    product = Product(contentList)
    return product


if __name__ == "__main__":
    query_assist_script()
