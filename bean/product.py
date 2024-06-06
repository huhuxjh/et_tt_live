import random
import re


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

    def dumps(self):
        return {
            'index': self.index, 'text': self.text,
            'llm_infer': self.llm_infer, 'tts_type': self.tts_type,
            'vid_label': self.vid_label, 'wav': self.wav,
        }


class Script:
    def __init__(self, context, sys_inst, role_play, item_list: list[ScriptItem]):
        self.context = context
        self.sys_inst = sys_inst
        self.role_play = role_play
        self.item_list = item_list
        # 调整roleplay
        self.role_play_prd = self._produce_roleplay_()

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
        self.script_config: list[str] = [
            # 'product_summary[2]'
            'product_summary[2]', 'order_urging', 'product_summary[2]', 'order_urging',
            'product_details[2]', 'product_welfare', 'product_details[3]', 'product_welfare', 'order_urging',
            'product_details[2]', 'product_welfare', 'product_details[2]', 'product_welfare', 'order_urging',
            'product_welfare[3]', 'order_urging'
        ]

    def produce_script(self) -> list[ScriptItem]:
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
        script_item_list = [item.update(idx+1) for idx, item in enumerate(script_item_list)]
        # 返回生成的脚本列表
        return script_item_list



