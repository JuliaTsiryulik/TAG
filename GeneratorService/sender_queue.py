import pika
import threading

class SenderQueue:
    def __init__(self, queue_name):
        self._key_lock = threading.Lock()
        self.queue_name = queue_name

    def connect(self, login='tag', password='tag', ip_adress='192.168.0.102', port=5672):
        
        self.login = login
        self.password = password
        self.ip_adress = ip_adress
        self.port = port

        credentials = pika.PlainCredentials(login, password)
        parameters = pika.ConnectionParameters(ip_adress, port, '/', credentials)

        self.connection = pika.BlockingConnection(parameters)

        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)

    def send_message(self, message):
        
        with self._key_lock: #Блокировка (critical section)

            while True:
                try:
                    self.channel.basic_publish(exchange='',
                                               routing_key=self.queue_name,
                                               body=message,
                                               properties=pika.BasicProperties(delivery_mode=2))
                    break
                except pika.exceptions.StreamLostError:
                    print('connection closed... and restarted')
                    self.connect(self.login, self.password, self.ip_adress, self.port)
                except ConnectionResetError:
                    print('connection closed... and restarted')
                    self.connect(self.login, self.password, self.ip_adress, self.port)
                except pika.exceptions.ConnectionClosed:
                    print('connection closed... and restarted')
                    self.connect(self.login, self.password, self.ip_adress, self.port)
                except pika.exceptions.ConnectionOpenAborted:
                    print('connection closed... and restarted')
                    self.connect(self.login, self.password, self.ip_adress, self.port)


    def close(self):
        self.connection.close()




