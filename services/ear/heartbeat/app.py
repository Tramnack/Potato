import time

from services.ear.abstract_ear import AbstractEar
from services.shared_libs.RabbitMQ import RMQ_HOST, RMQ_PORT


class HeartbeatEar(AbstractEar):

    def _setup(self):
        pass

    def start_listening(self):
        try:
            i = 0
            while True:
                i += 1
                user_input = f"Message Nr.{i}"
                message = user_input.encode()
                self.publish(message, 'ear_to_brain')
                print(f" [x] Ear sent '{user_input}' to Brain")
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def main():
    producer = HeartbeatEar(RMQ_HOST, RMQ_PORT)
    success = producer.connect()
    if success:
        producer.start_listening()


if __name__ == '__main__':
    main()
