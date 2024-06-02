import json
import os
import pathlib
import pika

from tenacity import Retrying, RetryError, stop_after_attempt

import ControlNet
import Lora

APP_DIR = pathlib.Path(__file__).parent.resolve()
HUGGINGFACE_CACHE_DIR = APP_DIR / "../storage/cache"
HUGGINGFACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class Consumer:
    # https://www.rabbitmq.com/tutorials/tutorial-two-python
    # https://www.rabbitmq.com/tutorials/tutorial-six-python

    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue_name = 'main'

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
            self.channel.queue_declare(
                queue=self.queue_name, 
                durable=True
            )

    def on_request(self, channel, method, properties, body):
        params = json.loads(body)

        task = params.pop('task')
        error = ''
        result = None

        try:
            if task == 'model_train':
                result = model_train(**params)
            elif task == 'model_inference':
                result = model_inference_Lora(**params)
        except Exception as e:
            error = str(e)

        # convert pathlib.Path objects to strings
        if result:
            result = [str(item.resolve()) for item in result]

        try:
            for attempt in Retrying(stop=stop_after_attempt(3)):
                with attempt:
                    channel.basic_publish(
                        exchange='',
                        routing_key=properties.reply_to,
                        properties=pika.BasicProperties(
                            correlation_id=properties.correlation_id
                        ),
                        body=json.dumps({
                            'result': result,
                            'error': error
                        })
                    )
        except RetryError as e:
            print(e)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def wait_messages(self):
        self.channel.basic_consume(
            queue=self.queue_name, 
            on_message_callback=self.on_request
        )
        self.channel.start_consuming()
       
    def disconnect(self):
        if self.connection:
            self.channel.stop_consuming()
            self.channel.close()
            self.connection.close()
        
        self.connection = None
        self.channel = None


def model_train(model_dir: str, prompt: str, model_name: str = 'Lora', type_person: str = 'women') -> list[str]:
    if model_name == 'Lora':
        instance = Lora.DreamBoth_LoRA(
            model_dir=model_dir, 
            cache_dir=HUGGINGFACE_CACHE_DIR, 
            prompt=prompt, 
            type_person=type_person
        )
        instance.train()
        return instance.inference()
    elif model_name == 'ControlNet':
        instance = ControlNet.ControlNet(
            model_dir=model_dir, 
            cache_dir=HUGGINGFACE_CACHE_DIR, 
            prompt=prompt
        )
        instance.get_model()
        return instance.generate()
    

def model_inference_Lora(model_dir: str, prompt: str, type_person: str = 'women') -> list[str]:
    instance = Lora.DreamBoth_LoRA(
        model_dir=model_dir, 
        cache_dir=HUGGINGFACE_CACHE_DIR, 
        prompt=prompt, 
        type_person=type_person
    )
    return instance.inference()
