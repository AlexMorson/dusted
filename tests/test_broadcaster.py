from unittest import TestCase
from unittest.mock import Mock

from dusted.broadcaster import Broadcaster


class TestBroadcaster(TestCase):
    def test_multiple_subscribers(self):
        """Test that multiple subscribers get notified."""

        broadcaster = Broadcaster()
        mock_callback_1 = Mock(spec_set=[])
        mock_callback_2 = Mock(spec_set=[])
        broadcaster.subscribe(mock_callback_1)
        broadcaster.subscribe(mock_callback_2)

        broadcaster.broadcast()

        mock_callback_1.assert_called_once()
        mock_callback_2.assert_called_once()

    def test_nested_batch(self):
        """Test that nested batching works."""

        broadcaster = Broadcaster()
        mock_callback = Mock(spec_set=[])
        broadcaster.subscribe(mock_callback)

        with broadcaster.batch():
            with broadcaster.batch():
                broadcaster.broadcast()
            broadcaster.broadcast()

            mock_callback.assert_not_called()

        mock_callback.assert_called_once()
