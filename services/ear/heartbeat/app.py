import os
import time

from services.ear.abstract_ear import AbstractEar


class HeartbeatEar(AbstractEar):

    def setup(self):
        pass

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
    RMQ_HOST = os.getenv('RMQ_HOST', 'localhost')
    RMQ_PORT = int(os.getenv('RMQ_PORT', 5672))  # Also good to make port dynamic

    producer = HeartbeatEar(RMQ_HOST, RMQ_PORT)
    producer.start_listening()


if __name__ == '__main__':
    main()
