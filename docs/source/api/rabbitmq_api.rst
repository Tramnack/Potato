.. _rabbitmq_api:

RabbitMQ API & Message Flows
============================

General Principles
------------------
* All messages are JSON-encoded.
* Messages use persistent delivery mode (2) for durability.
* Queues are declared as durable.
* Error handling for failed message processing involves dead-lettering. (Link to a Dead Letter Queue section if you implement it).
* Active Services (Sender or Requester) define the message schema.

Message Broker Overview
-----------------------
The central message broker is RabbitMQ. Services connect using the `RMQ_HOST` and `RMQ_PORT` environment variables.

Flow 1: Ear to Brain
--------------------
* **Purpose:** To send recognized text from an Ear service to a Brain service for processing.
* **Publisher:** Any Ear implementation (e.g., :py:class:`~services.ear.abstract_ear.AbstractEar` ).
* **Consumer:** Any Brain implementation (e.g., :py:class:`~services.brain.abstract_brain.AbstractBrain` ).
* **Exchange:** `''` (default direct exchange)
* **Queue:** TBD
* **Routing Key:** TBD
* **Message Format:** :py:class:`~services.shared_libs.common_types.EarOutputMessage`.
    * Example payload:
        TBD

..
  Flow 2: Brain to Mouth

Error Handling (Dead Letter Queues)
-----------------------------------
TBD