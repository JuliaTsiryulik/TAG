import json

class SoundRequest:
    def __init__(self, chatid=None, userid=None, duration=None, message=None):
        self.chatid = chatid
        self.userid = userid
        self.duration = duration
        self.message = message

    def json_create(self):
        data = {'chatid':self.chatid, 'userid':self.userid, 'duration':self.duration, 'message':self.message}
        json_data = json.dumps(data)
        return json_data

    def json_parse(self, text):
        data = json.loads(text)
        for key, value in data.items():
            setattr(self, key, value)
        return self

