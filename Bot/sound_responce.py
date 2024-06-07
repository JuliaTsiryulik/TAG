import json

class SoundResponce:
    def __init__(self, chatid=None, userid=None, sound=None):
        self.chatid = chatid
        self.userid = userid
        self.sound = sound

    def json_create(self):
        data = {'chatid':self.chatid, 'userid':self.userid, 'sound':self.sound}
        json_data = json.dumps(data)
        return json_data

    def json_parse(self, text):
        data = json.loads(text)
        for key, value in data.items():
            setattr(self, key, value)
        return self

