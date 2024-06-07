import pika
import base64
import time
from sender_queue import SenderQueue
from sound_request import SoundRequest
from sound_responce import SoundResponce
from model import sound_predict

responce_queue = SenderQueue('responce_queue')
responce_queue.connect(ip_adress='localhost')


class SoundGeneratorService:
    def __init__(self):
        self.sent = set()
        self.required_reconnect = False

    def connect_and_consume(self, login='tag', password='tag', ip_adress='localhost', port=5672):

        self.login = login
        self.password = password
        self.ip_adress = ip_adress
        self.port = port

        credentials = pika.PlainCredentials(login, password)
        parameters = pika.ConnectionParameters(ip_adress, port, '/', credentials)

        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='requests_queue', durable=True)

        print(' [*] Waiting for messages. To exit press CTRL+C')

        self.channel.basic_consume('requests_queue', self.callback)

        try:
            self.channel.start_consuming()

            self.required_reconnect = False
        except:
            self.required_reconnect = True

    def callback(self, ch, method, properties, body):

        if (body in self.sent):
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.sent.remove(body)
            return

        print(" [x] Received %r" % (body,))
        request = SoundRequest().json_parse(body.decode('utf-8')) #get attrs

        binary_sound_data = sound_predict(request.message, request.duration)
        sound_data = base64.b64encode(binary_sound_data).decode('utf-8')

        responce = SoundResponce(request.chatid, request.userid, sound_data).json_create()
        responce_queue.send_message(responce)
        self.sent.add(body)

        try:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.sent.remove(body)
        except:
            pass

    def close(self):
        self.responce_queue.close()


service = SoundGeneratorService()

while True:
    service.connect_and_consume()

    if service.required_reconnect == False:#Если вышли по причине ошибки обработки очереди, то пробуем переподключиться заново
        break


service.close()