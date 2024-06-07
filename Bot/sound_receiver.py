import telebot
import pika
import base64
from secrets import secrets
from sound_responce import SoundResponce
from context import Context

"""
Будет работать в отдельном потоке. 
Для чего нужно: этот код будет запускаться вместе с ботом, 
                но тк бот повесит основной поток, 
                то эту часть будем запускать в отдельном потоке 
                для возможности одновременной работы бота и приема сообщений из очереди.
"""

class SoundReceiver:
    def __init__(self, bot, users_context, after_sent_callback):
        self.bot = bot
        self.users_context = users_context
        self.after_sent_callback = after_sent_callback

    def connect(self, login='tag', password='tag', ip_adress='192.168.0.102', port=5672):

        credentials = pika.PlainCredentials(login, password)
        parameters = pika.ConnectionParameters(ip_adress, port, '/', credentials)

        connection = pika.BlockingConnection(parameters)
        self.channel = connection.channel()

        self.channel.queue_declare(queue='responce_queue', durable=True)

    def callback(self, ch, method, properties, body):
        receive = SoundResponce().json_parse(body.decode('utf-8'))

        sound = base64.b64decode(receive.sound)
        self.bot.send_audio(receive.chatid, sound)

        ch.basic_ack(delivery_tag=method.delivery_tag)

        self.users_context.reset_data(receive.userid, receive.chatid)

        self.after_sent_callback(receive.userid, receive.chatid)

    def process(self):
        self.channel.basic_consume('responce_queue', self.callback)
        self.channel.start_consuming()

#Check tonight
def receive_sound(bot, users_context, after_sent_callback):
    sound = SoundReceiver(bot, users_context, after_sent_callback)
    sound.connect()
    sound.process()


