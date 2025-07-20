import time

from services.ear.abstract_ear import AbstractEar
from services.shared_libs.RabbitMQ import RMQ_HOST, RMQ_PORT


class HeartbeatEar(AbstractEar):

    def setup(self):
        self.ready = True  # For HealthCheck

    def start_listening(self):
        try:
            i = 0
            while True:
                i += 1
                user_input = f"Message Nr.{i}"
                message = user_input.encode()
                self.publish('ear_to_brain', message)
                print(f" [x] Ear sent '{user_input}' to Brain")
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def main():
    producer = HeartbeatEar(RMQ_HOST, RMQ_PORT)
    producer.start_listening()


if __name__ == '__main__':
    main()
