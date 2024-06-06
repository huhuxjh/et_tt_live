import json
import os.path
import random
import re
import shutil


class Config:
    def __init__(self, room_name, browser_id, product_sheet, product_range,
                 assist_sheet, assist_range, ref_speaker, sound_device):
        self.room_name = room_name
        self.browser_id = browser_id
        self.product_sheet = product_sheet
        self.product_range = product_range
        self.assist_sheet = assist_sheet
        self.assist_range = assist_range
        self.ref_speaker = ref_speaker
        self.sound_device = sound_device


class ScriptItem:
    def __init__(self, index, text, llm_infer, tts_type, vid_label, wav=''):
        self.index = index
        self.text = text
        self.llm_infer = llm_infer
        self.tts_type = tts_type
        self.vid_label = vid_label
        self.wav = wav

    def update(self, idx):
        self.index = idx
        return self

    def dumps(self) -> dict:
        return {
            'index': self.index, 'text': self.text,
            'llm_infer': self.llm_infer, 'tts_type': self.tts_type,
            'vid_label': self.vid_label, 'wav': self.wav,
        }

    def from_dict(dict_item: dict):
        return ScriptItem(
            index=dict_item['index'],
            text=dict_item['text'],
            llm_infer=dict_item['llm_infer'],
            tts_type=dict_item['tts_type'],
            vid_label=dict_item['vid_label'],
            wav=dict_item['wav'],
        )


class Script:
    def __init__(self, context, sys_inst, role_play, item_list: list[ScriptItem], role_play_prd=None):
        self.context = context
        self.sys_inst = sys_inst
        self.role_play = role_play
        self.item_list = item_list
        # 调整roleplay
        if role_play_prd:
            self.role_play_prd = role_play_prd
        else:
            self.role_play_prd = self._produce_roleplay_()
        # 记录缓存位置
        self._config_path_ = None

    def _produce_roleplay_(self):
        role_play = '\n'.join([f'{val.index}.{val.text}' for idx, val in enumerate(self.item_list)])
        role_play = f'{self.role_play}\n{role_play}'
        return role_play

    def dumps(self):
        return {
            'context': self.context, 'sys_inst': self.sys_inst,
            'role_play': self.role_play, 'role_play_prd': self.role_play_prd,
            'item_list': [item.dumps() for item in self.item_list],
        }

    def to_file(self, json_file):
        with open(json_file, 'w', encoding='utf8', errors='ignore') as fd:
            fd.write(json.dumps(self.dumps()))
        self._config_path_ = json_file

    def from_file(json_file: str):
        with open(json_file, 'r', encoding='utf8', errors='ignore') as fd:
            json_dict = json.loads(fd.read())
        # rebuild
        script = Script(
            context=json_dict['context'],
            sys_inst=json_dict['sys_inst'],
            role_play=json_dict['role_play'],
            item_list=[ScriptItem.from_dict(item) for item in json_dict['item_list']],
            role_play_prd=json_dict['role_play_prd'],
        )
        script._config_path_ = json_file
        return script

    def commit(self):
        audio_list = [item.wav for item in self.item_list if item.wav != '' and os.path.exists(item.wav)]
        base_dir = os.path.dirname(self._config_path_)
        for audio in audio_list:
            name = os.path.basename(audio)
            shutil.copy(audio, os.path.join(base_dir, name))
        # 更新缓存文件
        self.to_file(self._config_path_)


class TemplateItem:
    def __init__(self, template_tag, text, llm_infer, tts_type, vid_label):
        self.template_tag = template_tag
        self.text = text
        self.llm_infer = llm_infer
        self.tts_type = tts_type
        self.vid_label = vid_label


class Template:
    def __init__(self, context, sys_inst, role_play, item_group: dict[str, list[TemplateItem]]):
        self.context = context
        self.sys_inst = sys_inst
        self.role_play = role_play
        self.item_group = item_group
        # todo: 从网络更新配置
        self.template_tag_group = {
            'welcome': ['welcome'],
            'selling_point': ['selling_point_1', 'selling_point_2', 'selling_point_3', 'selling_point_4'],
            'chat': ['chat_1', 'chat_2'],
            'order_urging': ['order_urging'],
            'bye': ['bye'],
        }
        # for (指定)count 1000
        #     (判断有没有,0.5中概率,0-1) 随机welcome...n (去重)
        #     随机selling_point_n (去重)
        #     (判断有没有, 0.4中概率, 0-1) 随机selling_point_n(去重)
        #     (判断有没有, 0.3小概率, 0-1) 随机selling_point_n(去重)
        #     (判断有没有,0.1小概率,0-1) 随机是否要插入chat (去重)
        #     (判断有没有,0.8大概率,0-1) 随机是否要插入order_urging (去重)
        # 'bye'
        self.script_config: list[str] = self.produce_config()

    def produce_config(self, seed=1000) -> list[str]:
        """
        根据规则生成本场脚本配置文件
        """
        config_tas_list = []
        for idx in range(seed):
            # welcome
            if len(config_tas_list) <= 0 or random.random() <= 0.5:
                config_tas_list.append(random.choice(self.template_tag_group['welcome']))
            # selling_point
            selling_sample = random.sample(self.template_tag_group['selling_point'], 3)
            config_tas_list.append(selling_sample[0])
            if random.random() <= 0.4:
                config_tas_list.append(selling_sample[1])
            if random.random() <= 0.3:
                config_tas_list.append(selling_sample[2])
            # chat
            if random.random() <= 0.1:
                config_tas_list.append(random.choice(self.template_tag_group['chat']))
            # order_urging
            if random.random() <= 0.8:
                config_tas_list.append(random.choice(self.template_tag_group['order_urging']))
        # bye
        config_tas_list.append(random.choice(self.template_tag_group['bye']))
        # 返回config
        return config_tas_list

    def produce_script(self) -> list[ScriptItem]:
        """
        根据配置生成脚本
        """
        def convert(template_item: TemplateItem):
            template_item = ScriptItem(index=0, text=template_item.text, llm_infer=template_item.llm_infer,
                                       tts_type=template_item.tts_type, vid_label=template_item.vid_label)
            return template_item

        script_item_list = []
        # 根据配置生成script列表
        pattern = re.compile(r'\[(\d+)\]')
        for template_config in self.script_config:
            choice_piece = 1
            match = pattern.findall(template_config, -1)
            if match: choice_piece = int(match[0])
            choice_tag = re.sub(pattern, '', template_config)
            if choice_tag in self.item_group:
                choice_group = self.item_group[choice_tag]
                choice_piece = min(choice_piece, len(choice_group))
                choice_list = random.sample(choice_group, choice_piece)
                script_item_list.extend(map(convert, choice_list))
            else:
                print(f'tag {choice_tag} is not in template list')
        # 更新脚本步骤信息
        script_item_list = [item for item in script_item_list if item.text != '']
        script_item_list = [item.update(idx+1) for idx, item in enumerate(script_item_list)]
        # 返回生成的脚本列表
        return script_item_list

    def produce_script_all(self) -> list[ScriptItem]:
        """
        用于生产全部脚本tts内容
        """
        def convert(template_item: TemplateItem):
            template_item = ScriptItem(index=0, text=template_item.text, llm_infer=template_item.llm_infer,
                                       tts_type=template_item.tts_type, vid_label=template_item.vid_label)
            return template_item

        script_item_list = []
        for key, val_list in self.item_group.items():
            script_item_list.extend(map(convert, val_list))
        # 更新脚本步骤信息
        script_item_list = [item for item in script_item_list if item.text != '']
        script_item_list = [item.update(idx + 1) for idx, item in enumerate(script_item_list)]
        # 返回生成的脚本列表
        return script_item_list

