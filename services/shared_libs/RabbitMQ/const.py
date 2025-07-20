import os

RMQ_HOST = os.getenv('RMQ_HOST', 'localhost')
RMQ_PORT = int(os.getenv('RMQ_PORT', 5672))
