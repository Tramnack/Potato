import os
import sys

from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic

from services.brain.abstract_brain import AbstractBrain


class EchoBrain(AbstractBrain):
    def setup(self):
        pass

    def callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        received_text = body.decode()
        print(f" [x] Brain received '{received_text}'")

        processed_text = f"Brain echoed: {received_text}"  # Simple echo logic
        self.publish('brain_to_mouth', processed_text.encode())
        print(f" [x] Brain sent '{processed_text}' to Mouth")

        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))

    consumer = EchoBrain(RABBITMQ_HOST, RABBITMQ_PORT)
    print(' [*] Brain waiting for messages. To exit press CTRL+C')
    consumer.consume('ear_to_brain', auto_ack=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            exit(0)
