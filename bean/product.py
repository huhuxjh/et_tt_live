class Product:
    def __init__(self, context, sys_inst, role_play_head, role_play, contentList):
        self.context = context
        self.sys_inst = sys_inst
        self.role_play_head = role_play_head
        self.role_play = role_play
        self.contentList = contentList


class ContentItem:
    def __init__(self, index, text, keep, spc_type, label, wav='', reproduce=True):
        self.index = index
        self.text = text
        self.keep = keep
        self.spc_type = spc_type
        self.label = label
        self.wav = wav
        self.reproduce = reproduce
