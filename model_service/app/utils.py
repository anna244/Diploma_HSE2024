import json
import os
import pathlib
import pika

import ControlNet
import Lora

APP_DIR = pathlib.Path(__file__).parent.resolve()
HUGGINGFACE_CACHE_DIR = APP_DIR / "../storage/cache"
HUGGINGFACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class Consumer:
    def __init__(self):
        self.connection = None
        self.channel = None

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
                    port=os.environ.get('RABBITMQ_PORT')
                )
            )

        self.create_channel()

    def create_channel(self):
        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='main', durable=True)
            self.wait_messages()

    def callback(self, channel, method, properties, body):
        params = json.loads(body)

        task = params.pop('task')

        if task == 'model_train':
            result = model_train(**params)
        elif task == 'model_inference':
            result = model_inference_Lora(**params)

        # convert pathlib.Path objects to strings
        result = [str(item.resolve()) for item in result]

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def wait_messages(self):
        self.channel.basic_consume(queue='main', on_message_callback=self.callback)
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
    

def model_inference_Lora(model_dir: str, promt: str, type_person: str = 'women') -> list[str]:
    instance = Lora.DreamBoth_LoRA(model_dir, promt, type_person)
    return instance.inference()
