import os, sys, json, subprocess, uuid, shutil, logging
from remote_config import lark_util
import tiktoklive.tiktok_live_util as tiktokUtil

config_src_range = 'B1:B8'


def start(browserId, scenes, product, ref_speaker_name, device_id, obs_port):
    print(f"{browserId}")
    tiktokUtil.startClient(browserId, scenes, product, ref_speaker_name, device_id, obs_port)


if __name__ == '__main__':
    configId = "okL6Yo"
    obs_port = 4455
    idx = 1
    while idx < len(sys.argv):
        if sys.argv[idx] == "--configId":
            configId = sys.argv[idx + 1]
        if sys.argv[idx] == "--obs_port":
            obs_port = sys.argv[idx + 1]
        idx += 1
    lark_util.request_tenant_token()
    datas = lark_util.query_range(configId, config_src_range)

    # 获取指纹浏览器ID
    browserId = datas[1][0]
    # 获取主播商品介绍sheetId
    product_sheet = datas[2][0]
    # 获取主播商品介绍sheet_range
    product_range = datas[3][0]
    # 获取助播公屏配置sheetId
    assist_sheet = datas[4][0]
    # 获取助播公屏配置sheet_range
    assist_range = datas[5][0]
    # 获取主播音色名字
    ref_speaker_name = datas[6][0]
    # ref_speaker_name = 'man_role0_ref'
    # 获取播放设备id
    device_id = datas[7][0]
    # device_id = 1

    print(
        f"browser: {browserId},\nproduct_sheet: {product_sheet},"
        f"\nproduct_range:{product_range},\nassist_sheet: {assist_sheet},\nassist_range:{assist_range}")
    # 获取商品脚本
    product = lark_util.query_product_script(product_sheet, product_range)
    # 获取助播脚本
    scenes = lark_util.query_assist_script(assist_sheet, assist_range)
    start(browserId, scenes, product, ref_speaker_name, device_id, obs_port)
