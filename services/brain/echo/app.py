import os
import sys

from services.shared_libs.RabbitMQ import RabbitMQConsumer, RabbitMQProducer

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))

def main():

    consumer = RabbitMQConsumer(RABBITMQ_HOST, RABBITMQ_PORT)
    print(' [*] Brain waiting for messages. To exit press CTRL+C')
    consumer.consume('ear_to_brain', callback, auto_ack=False)


def callback(ch, method, properties, body):
    received_text = body.decode()
    print(f" [x] Brain received '{received_text}'")
    processed_text = f"Brain echoed: {received_text}"  # Simple echo logic

    producer = RabbitMQProducer(RABBITMQ_HOST, RABBITMQ_PORT)
    producer.publish('brain_to_mouth', processed_text.encode())
    print(f" [x] Brain sent '{processed_text}' to Mouth")
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            exit(0)
