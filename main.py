import os, sys, json, subprocess, uuid, shutil, logging
from remote_config import lark_util
import tiktoklive.tiktok_live_util as tiktokUtil

config_src_range = 'B1:B9'


def start(browserId, scenes, product, ref_speaker_name, device_id, obs_port, mode, configId):
    print(f"{browserId}")
    tiktokUtil.startClient(browserId, scenes, product, ref_speaker_name, device_id, obs_port, mode, configId)


if __name__ == '__main__':
    configId = "okL6Yo"
    obs_port = 4455
    # 0: live 实时生成 
    # 1: prepare 直播前准备 
    # 2: play prepare 播放准备素材
    mode = 0 

    idx = 1
    while idx < len(sys.argv):
        if sys.argv[idx] == "--configId":
            configId = sys.argv[idx + 1]
        if sys.argv[idx] == "--obs_port":
            obs_port = int(sys.argv[idx + 1])
        if sys.argv[idx] == "--mode":
            mode = sys.argv[idx + 1]
        idx += 1
   
    lark_util.request_tenant_token()
    datas = lark_util.query_range(configId, config_src_range)

    # 获取直播间名字
    roomName = datas[1][0]
    # 获取指纹浏览器ID
    browserId = datas[2][0]
    # 获取主播商品介绍sheetId
    product_sheet = datas[3][0]
    # 获取主播商品介绍sheet_range
    product_range = datas[4][0]
    # 获取助播公屏配置sheetId
    assist_sheet = datas[5][0]
    # 获取助播公屏配置sheet_range
    assist_range = datas[6][0]
    # 获取主播音色名字
    ref_speaker_name = datas[7][0]
    # ref_speaker_name = 'man_role0_ref'
    # 获取播放设备id
    device_id = datas[8][0]
    # device_id = 1

    print(
        f"browser: {browserId},\nproduct_sheet: {product_sheet},"
        f"\nproduct_range:{product_range},\nassist_sheet: {assist_sheet},\nassist_range:{assist_range}")
    # 获取商品脚本
    template = lark_util.query_product_template(product_sheet, product_range)
    # reproduce_list = [1,9,10,14,15,18,28,32,33,34,40,42,44,47,56,62,65,67,69,70,73,75,76,79,84,94,98,100,
    #                   107,111,112,114,126,127,130,135,135,138,142,149,155,156,159,160,161,163,164]
    # for item in product.contentList:
    #     item.reproduce = (item.index in reproduce_list)
    product = lark_util.product_product_scrip(template)
    # print(product.dumps())
    # 获取助播脚本
    scenes = lark_util.query_assist_script(assist_sheet, assist_range)
    start(browserId, scenes, product, ref_speaker_name, device_id, obs_port, mode, configId)
