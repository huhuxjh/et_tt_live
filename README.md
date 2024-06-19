# et_tt_live
Tool for tiktok live.
    
    直播前先预生成一场
    python main.py --run_mode 1 --config_id xxx
    
    生成后，直播时执行
    python main.py --run_mode 2 --config_id xxx
    
    # run_mode
    # 0: live 实时生成
    # 1: prepare 直播前准备 
    # 2: play prepare 播放准备素材

    # config_id 直播间配置ID，见飞书文档