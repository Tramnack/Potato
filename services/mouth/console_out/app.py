import sys

from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic

from services.mouth.abstract_mouth import AbstractMouth
from services.shared_libs.RabbitMQ import RMQ_HOST, RMQ_PORT


class ConsoleOutMouth(AbstractMouth):
    def _setup(self):
        pass

    def _callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        received_text = body.decode()
        print(f" [x] Mouth received '{received_text}'")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _handle_unacknowledged_messages(self, un_acknowledged) -> None:
        pass


def main():
    consumer = ConsoleOutMouth("brain_to_mouth", RMQ_HOST, RMQ_PORT)
    success = consumer.connect()
    if success:
        print(' [*] Mouth waiting for messages. To exit press CTRL+C')
        consumer.consume(auto_ack=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            exit(0)
