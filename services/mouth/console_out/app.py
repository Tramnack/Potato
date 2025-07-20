import os
import sys

from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic

from services.mouth.abstract_mouth import AbstractMouth


class ConsoleOutMouth(AbstractMouth):
    def setup(self):
        pass

    def callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        received_text = body.decode()
        print(f" [x] Mouth received '{received_text}'")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    RMQ_HOST = os.getenv('RMQ_HOST', 'localhost')
    RMQ_PORT = int(os.getenv('RMQ_PORT', 5672))

    consumer = ConsoleOutMouth(RMQ_HOST, RMQ_PORT)
    print(' [*] Mouth waiting for messages. To exit press CTRL+C')
    consumer.consume('brain_to_mouth', auto_ack=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            exit(0)
