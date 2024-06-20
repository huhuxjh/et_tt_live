import sys
from remote_config import lark_util
import tiktoklive.tiktok_live_util as live_util
import tiktoklive.tiktok_prepare_util as prepare_util

# run_mode
# 0: live 实时生成
# 1: prepare 直播前准备
# 2: play prepare 播放准备素材
def process(config_id, config_src_range, obs_video_port, obs_audio_port, run_mode, local_video_dir):
    if run_mode == 0:
        reproduce = True
        interactive = True
    elif run_mode == 1:
        reproduce = True
        interactive = False
    else:  
        reproduce = False
        interactive = True

    # 参数对照
    print(f'config_id={config_id}, '
          f'obs_video_port={obs_video_port},'
          f'obs_audio_port={obs_audio_port}, '
          f'run_mode={run_mode}, '
          f'local_video_dir={local_video_dir}, '
          f'reproduce={reproduce}')

    # 请求配置
    config = lark_util.retrieve_config(config_id, config_src_range)

    print(f"browser: {config.browser_id},"
          f"product_sheet: {config.product_sheet},"
          f"product_range:{config.product_range},"
          f"assist_sheet: {config.assist_sheet},"
          f"assist_range:{config.assist_range}")

    # 获取商品脚本
    product = lark_util.retrieve_script(config_id, config.product_sheet, config.product_range, config.seed, reproduce)
    # 获取助播脚本
    scenes = lark_util.query_assist_script(config.assist_sheet, config.assist_range)
    # 启动main逻辑
    if run_mode == 1:
        prepare_util.start_prepare(product=product,configId=config_id,config=config)
        # 如果完成后, 更新缓存, 拷贝音频
        product.commit()
    else:
        live_util.start_live(scenes, product, obs_video_port, obs_audio_port, local_video_dir, run_mode, config_id, interactive, config)


if __name__ == '__main__':
    config_id = "okL6Yo"
    config_src_range = 'B1:B10'
    obs_video_port = 0
    obs_audio_port = 0
    # run_mode = 0

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
        idx += 1
    process(config_id, config_src_range, obs_video_port, obs_audio_port, run_mode)