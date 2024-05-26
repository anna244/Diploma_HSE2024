from utils import Consumer

if __name__ == '__main__':
    consumer = Consumer()
    try:
        consumer.connect()
        consumer.wait_messages()
    except KeyboardInterrupt:
        consumer.disconnect()
