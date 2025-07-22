import sys

import requests
from pika import BasicProperties
from pika.channel import Channel
from pika.spec import Basic

from services.brain.abstract_brain import AbstractBrain
from services.shared_libs.RabbitMQ import RMQ_HOST, RMQ_PORT


class SmolBrain(AbstractBrain):
    def _setup(self):
        pass

    def _callback(self, ch: Channel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
        received_text = body.decode()
        print(f" [x] Brain received '{received_text}'")

        processed_text = self.prompt(received_text)

        self.publish(processed_text.encode(), 'brain_to_mouth')
        print(f" [x] Brain sent '{processed_text}' to Mouth")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def prompt(self, content):
        url = "http://localhost:12434/engines/llama.cpp/v1/chat/completions"  # Local
        # url = "http://model-runner.docker.internal/engines/llama.cpp/v1/chat/completions" # Container
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "ai/smollm2",
            "messages": [
                {"role": "system", "content": "You are an unhelpful smol Potato Brain."},
                {"role": "user", "content": content}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        content = response.json()["choices"][0]["message"]["content"]
        return content

    def _handle_unacknowledged_messages(self, un_acknowledged) -> None:
        pass


def main():
    consumer = SmolBrain('brain_to_mouth', RMQ_HOST, RMQ_PORT)
    success = consumer.connect()
    if success:
        print(' [*] Brain waiting for messages. To exit press CTRL+C')
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
