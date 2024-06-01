import asyncio
import json
import os
import re
import uuid

import aio_pika
from tenacity import retry, stop_after_attempt


class Publisher:
    # https://aio-pika.readthedocs.io/en/latest/patterns.html#rpc
    # https://github.com/mosquito/aio-pika/blob/master/aio_pika/patterns/rpc.py

    def __init__(self):
        self.connection = None
        self.channel = None
        self.loop = None

        self.result_queue = None
        self.result_consumer_tag = None
        self.result_tasks = {}
        
        self.queue_name = 'main'

    async def connect(self):
        if not self.loop:
            self.loop = asyncio.get_event_loop()

        if not self.connection or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(
                f"amqp://{os.environ.get('RABBITMQ_DEFAULT_USER')}:{os.environ.get('RABBITMQ_DEFAULT_PASS')}@{os.environ.get('RABBITMQ_HOST')}:{os.environ.get('RABBITMQ_PORT')}/?heartbeat=0",
                client_properties={"connection_name": "caller"},
            )
        
        await self.create_channel()

    async def create_channel(self):
        if not self.channel or self.channel.is_closed:
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(self.queue_name, durable=True)

            self.result_queue = await self.channel.declare_queue(None, exclusive=True, auto_delete=True)

            self.result_consumer_tag = await self.result_queue.consume(
                self.on_response, 
                exclusive=True, 
                no_ack=True,
            )

    # https://github.com/mosquito/aio-pika/blob/master/aio_pika/patterns/rpc.py#L239
    def on_response(self, message):
        if message.correlation_id is None:
            return
        task = self.result_tasks.pop(message.correlation_id, None)
        if task is None:
            return
        payload = json.loads(message.body)
        task.set_result(payload)

    # https://stackoverflow.com/questions/50246304/using-python-decorators-to-retry-request
    @retry(stop=stop_after_attempt(3))
    async def send_message(self, payload):
        await self.connect()

        task = self.loop.create_future()
        correlation_id = str(uuid.uuid4())
        self.result_tasks[correlation_id] = task
        task.add_done_callback(
            lambda *args, **kwargs: self.result_tasks.pop(correlation_id, None)
        )

        # https://github.com/mosquito/aio-pika/blob/master/aio_pika/patterns/rpc.py#L365
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload, ensure_ascii=False).encode(),
                correlation_id=correlation_id,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                reply_to=self.result_queue.name,
            ),
            routing_key=self.queue_name,
        )
        
        return await task
        
    async def disconnect(self):
        for task in self.result_tasks.values():
            if task.done():
                continue
            task.set_exception(Exception)

        if self.result_queue and self.result_consumer_tag:
            await self.result_queue.cancel(self.result_consumer_tag)
            await self.result_queue.delete()

        if self.channel and not self.channel.is_closed:
            self.channel.close()

        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        
        self.result_consumer_tag = None
        self.result_queue = None
        self.channel = None
        self.connection = None


def translit(text: str) -> str:
    pattern = re.compile(r'[\W]+')
    return pattern.sub("", text)
