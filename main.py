import sys
from remote_config import lark_util
import tiktoklive.tiktok_live_util as tiktokUtil


def start(browser_id, scenes, product, ref_speaker_name, device_id, obs_port, mode, config_id):
    print(f"{browser_id}")
    tiktokUtil.startClient(browser_id, scenes, product, ref_speaker_name, device_id, obs_port, mode, config_id)


if __name__ == '__main__':
    config_id = "okL6Yo"
    config_src_range = 'B1:B9'
    obs_port = 4455
    # 0: live 实时生成 
    # 1: prepare 直播前准备 
    # 2: play prepare 播放准备素材
    run_mode = 0

    idx = 1
    while idx < len(sys.argv):
        if sys.argv[idx] == "--configId":
            config_id = sys.argv[idx + 1]
        if sys.argv[idx] == "--obs_port":
            obs_port = int(sys.argv[idx + 1])
        if sys.argv[idx] == "--mode":
            run_mode = sys.argv[idx + 1]
        idx += 1
   
    lark_util.request_tenant_token()
    data_sheet = lark_util.query_range(config_id, config_src_range)

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
    ref_speaker_name = data_sheet[7][0]
    # ref_speaker_name = 'man_role0_ref'
    # 获取播放设备id
    device_id = data_sheet[8][0]
    # device_id = 1

    print(
        f"browser: {browser_id},\nproduct_sheet: {product_sheet},"
        f"\nproduct_range:{product_range},\nassist_sheet: {assist_sheet},\nassist_range:{assist_range}")
    # 获取商品脚本
    product = lark_util.retrieve_script(config_id, product_sheet, product_range)
    # 获取助播脚本
    scenes = lark_util.query_assist_script(assist_sheet, assist_range)
    start(browser_id, scenes, product, ref_speaker_name, device_id, obs_port, run_mode, config_id)
