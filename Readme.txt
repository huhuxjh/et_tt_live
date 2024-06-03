input: browserId: 'f190f0eaf9bc4265bfbfa60da3deed47' 以具体电脑上的浏览器id为准

实时产品介绍脚本，按scene1->2->-3->4的顺序不断循环

{
    "scenes": [
        {
            "name": "scene1",
            "content": 123456, //广播内容
            "start_time": 0,   //第一次开始的时间，单位是秒
            "cycle_time": 60   //循环播放的时间，单位是秒，不写或为0就认为只广播一次
        },
        {
            "name": "scene2",
            "content": 223456
            "start_time": 0,
            "cycle_time": 60
        },
        {
            "name": "scene3",
            "content": 543253,
            "start_time": 0,
            "cycle_time": 60
        },
        {
            "name": "scene4",
            "content": 123456,
            "start_time": 0,
            "cycle_time": 60
        }
    ]
}


