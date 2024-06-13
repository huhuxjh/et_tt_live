import sys
from remote_config import lark_util
import tiktoklive.tiktok_live_util as tiktokUtil


def start(browser_id, scenes, product, ref_speaker_name, device_id, obs_video_port,obs_audio_port, mode, config_id, interactive):
    print(f"{browser_id}")
    tiktokUtil.startClient(browser_id, scenes, product, ref_speaker_name, device_id, obs_video_port,obs_audio_port, mode, config_id, interactive)


if __name__ == '__main__':
    config_id = "okL6Yo"
    config_src_range = 'B1:B10'
    obs_video_port = 4455
    obs_audio_port = 4455
    # 0: live 实时生成
    # 1: prepare 直播前准备 
    # 2: play prepare 播放准备素材
    #  是否重新生成script
    reproduce = False

    # 是否加入互动
    interactive = False

    idx = 1
    while idx < len(sys.argv):
        if sys.argv[idx] == "--config_id":
            config_id = sys.argv[idx + 1]
        elif sys.argv[idx] == "--obs_video_port":
            obs_video_port = int(sys.argv[idx + 1])
        elif sys.argv[idx] == "--obs_audio_port":
            obs_audio_port = int(sys.argv[idx + 1])
        elif sys.argv[idx] == "--run_mode":
            run_mode = int(sys.argv[idx + 1])
        elif sys.argv[idx] == '--force':
            reproduce = sys.argv[idx + 1] == 'True'
        idx += 1
    # 参数对照
    print(f'config_id={config_id}, obs_video_port={obs_video_port},obs_audio_port={obs_audio_port}, run_mode={run_mode}, reproduce={reproduce}')
    # 请求配置
    config = lark_util.retrieve_config(config_id, config_src_range)
    print(f"browser: {config.browser_id},\nproduct_sheet: {config.product_sheet},product_range:{config.product_range},"
          f"\nassist_sheet: {config.assist_sheet},assist_range:{config.assist_range}")
    # 获取商品脚本
    product = lark_util.retrieve_script(config_id, config.product_sheet, config.product_range, config.seed, reproduce)
    # 获取助播脚本
    scenes = lark_util.query_assist_script(config.assist_sheet, config.assist_range)
    # 启动main逻辑
    start(config.browser_id, scenes, product, config.ref_speaker, config.sound_device, obs_video_port, obs_audio_port, run_mode, config_id, interactive)
    # 如果完成后, 更新缓存, 拷贝音频
    product.commit()
