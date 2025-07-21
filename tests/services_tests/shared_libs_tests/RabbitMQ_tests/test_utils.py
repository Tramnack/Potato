from unittest.mock import patch, MagicMock

import pytest


def main():
    pass


if __name__ == '__main__':
    main()


@pytest.fixture
def mock_pika():
    """A fixture to mock the pika.BlockingConnection and its components."""

    def close_connection(connection):
        setattr(connection, 'is_open', False)
        setattr(connection.channel.return_value, 'is_open', False)

    with patch('pika.BlockingConnection') as mock_blocking_connection:
        mock_connection = MagicMock()
        mock_connection.is_open = True
        mock_connection.close.side_effect = lambda: close_connection(mock_connection)

        mock_channel = MagicMock()
        mock_channel.is_open = True

        mock_connection.channel.return_value = mock_channel
        mock_blocking_connection.return_value = mock_connection

        yield mock_blocking_connection, mock_connection, mock_channel
