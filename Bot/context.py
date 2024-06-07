import threading

#Хранит в рамках каждого пользователя информацию о сообщении и признак того, что сообщение было отправлено, если контекста не будет == в глобальных переменных, то данные пользователей перемешаются  
class Context:
    def __init__(self):
        self.context = {}
        self._key_lock = threading.Lock()

    def reset_data(self, user_id, chat_id):
        with self._key_lock:
            if ((user_id, chat_id) in self.context) == False:
                return 
            self.context.pop((user_id, chat_id))
    
    def add_data(self, user_id, chat_id, **kwargs):
        with self._key_lock:
            if ((user_id, chat_id) in self.context) == False:
                self.context[(user_id, chat_id)] = {}

            self.context[(user_id, chat_id)].update(kwargs)

    def get_data(self, user_id, chat_id):
        with self._key_lock:
            if ((user_id, chat_id) in self.context) == False:
                return None
            return self.context[(user_id, chat_id)]

