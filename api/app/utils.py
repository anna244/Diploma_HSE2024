import json
import os
import re
import uuid

import pika
from tenacity import retry, stop_after_attempt


class Publisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.callback_queue = None

    def connect(self):
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    # https://pika.readthedocs.io/en/stable/intro.html#credentials
                    credentials=pika.PlainCredentials(
                        os.environ.get('RABBITMQ_DEFAULT_USER'), 
                        os.environ.get('RABBITMQ_DEFAULT_PASS')
                    ),
                    host=os.environ.get('RABBITMQ_HOST'),
                    port=os.environ.get('RABBITMQ_PORT'),
                    heartbeat=0
                )
            )
        
        self.create_channel()

    def create_channel(self):
        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='main', durable=True)

            result = self.channel.queue_declare(queue='', exclusive=True)
            self.callback_queue = result.method.queue


    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    # https://stackoverflow.com/questions/50246304/using-python-decorators-to-retry-request
    @retry(stop=stop_after_attempt(3))
    async def send_message(self, params):
        self.connect()

        correlation_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange='',
            routing_key='main',
            body=json.dumps(params),
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=correlation_id,
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return int(self.response)
        
    def disconnect(self):
        if self.channel and self.channel.is_open:
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()
        
        self.channel = None
        self.connection = None


def translit(text: str) -> str:
    pattern = re.compile(r'[\W]+')
    return pattern.sub("", text)
