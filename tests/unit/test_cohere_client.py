import pytest
from unittest.mock import patch, MagicMock
from pipeline.LLM.cohere_client import CohereClient


class TestCohereClient:
    @patch('pipeline.LLM.cohere_client.os.getenv')
    def test_missing_api_key(self, mock_getenv):
        mock_getenv.return_value = None
        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "test"}]
        with pytest.raises(ValueError, match="COHERE_API_KEY is not set."):
            list(CohereClient.cohere_chat(messages))

    @patch('pipeline.LLM.cohere_client.os.getenv')
    @patch('pipeline.LLM.cohere_client.cohere.ClientV2')
    def test_successful_stream(self, mock_cohere, mock_getenv):
        mock_getenv.return_value = "fake_key"

        # Setup mock client and stream
        mock_client_instance = MagicMock()
        mock_cohere.return_value = mock_client_instance

        # Create fake events for stream
        event1 = MagicMock()
        event1.type = "content-delta"
        event1.delta.message.content.text = "Hello "

        event2 = MagicMock()
        event2.type = "content-delta"
        event2.delta.message.content.text = "World!"

        mock_client_instance.chat_stream.return_value = [event1, event2]

        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}]
        generator = CohereClient.cohere_chat(messages)
        result = list(generator)

        assert result == ["Hello ", "World!"]
        mock_client_instance.chat_stream.assert_called_once()

    @patch('pipeline.LLM.cohere_client.os.getenv')
    @patch('pipeline.LLM.cohere_client.cohere.ClientV2')
    @patch('pipeline.LLM.cohere_client.Config')
    def test_retry_logic_failure(self, mock_config, mock_cohere, mock_getenv):
        mock_getenv.return_value = "fake_key"

        # Make the client fail repeatedly
        mock_client_instance = MagicMock()
        mock_client_instance.chat_stream.side_effect = Exception("API Error")
        mock_cohere.return_value = mock_client_instance

        # Override config variables without breaking wait_exponential float parsing
        mock_config.configure_mock(STOP_RETRY=2, RETRY_MIN_WAIT=0.01, RETRY_MAX_WAIT=0.05, MULTIPLIER=0.5)
        mock_config.COHERE_MODEL_NAME = "test-model"

        messages = [{"role": "user", "content": "Fail please"}]
        with pytest.raises(Exception, match="API Error"):
            # Have to consume the generator to trigger the code execution
            list(CohereClient.cohere_chat(messages))

        # Due to retries (2 attempts), it should have been called twice
        assert mock_client_instance.chat_stream.call_count == 2
