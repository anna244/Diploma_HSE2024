from utils import Consumer


if __name__ == '__main__':
    consumer = Consumer()
    try:
        consumer.connect()
    except KeyboardInterrupt:
        consumer.disconnect()
