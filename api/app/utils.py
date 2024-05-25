import re
import pika
import json
import os

class Publisher:
    def __init__(self):
        self.connection = None
        self.channel = None

    def connect(self):
        if self.connection:
            return
        
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                # https://pika.readthedocs.io/en/stable/intro.html#credentials
                credentials=pika.PlainCredentials(
                    os.environ.get('RABBITMQ_DEFAULT_USER'), 
                    os.environ.get('RABBITMQ_DEFAULT_PASS')
                ),
                host=os.environ.get('RABBITMQ_HOST'),
                port=os.environ.get('RABBITMQ_PORT')
            )
        )

        self.create_channel()

    def create_channel(self):
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='main', durable=True)

    def send_message(self, params):
        self.connect()

        self.channel.basic_publish(
            exchange='',
            routing_key='main',
            body=json.dumps(params),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        
    def disconnect(self):
        if self.connection:
            self.connection.close()
        
        self.connection = None
        self.channel = None


def translit(text: str) -> str:
    pattern = re.compile('[\W]+')
    return pattern.sub("", text)
