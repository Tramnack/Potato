import pika
import pytest

from services.shared_libs.RabbitMQ.RabbitMQStatefulMixin import RabbitMQStatefulMixin


class ConcreteRabbitMQStateful(RabbitMQStatefulMixin):

    def _retrieve_state(self, key: str) -> dict:
        return dict()

    def _update_state(self, key: str, state: dict) -> None:
        pass


class TestGetSessionIdFromProperties:

    @pytest.mark.parametrize("headers", [{"session_id": "test_session_id"}, {"session_id": 1234}])
    def test_get_session_id_from_properties(self, headers):
        instance = ConcreteRabbitMQStateful()

        test_properties = pika.BasicProperties(
            headers=headers
        )

        session_id = instance._get_session_id_from_properties(test_properties)
        assert session_id == str(headers["session_id"])

    @pytest.mark.parametrize("headers",
                             [{"session_id": None}, {"session_id": ""}, {"sesh_id": "test_session_id"}, {}, None])
    def test_get_session_id_from_bad_properties(self, headers):
        instance = ConcreteRabbitMQStateful()

        test_properties = pika.BasicProperties(
            headers=headers
        )

        session_id = instance._get_session_id_from_properties(test_properties)
        assert session_id is None

    @pytest.mark.parametrize("test_properties",
                             [{"headers": {"session_id": "test_session_id"}}, {"session_id": "test_session_id"}, None])
    def test_get_session_id_from_bad_property_type(self, test_properties):
        instance = ConcreteRabbitMQStateful()

        with pytest.raises(TypeError):
            instance._get_session_id_from_properties(test_properties)
