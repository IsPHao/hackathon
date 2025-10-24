import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from openai import AsyncOpenAI

from src.agents.voice_synthesizer import (
    VoiceSynthesizerAgent,
    VoiceSynthesizerConfig,
    ValidationError,
    SynthesisError,
    APIError,
)


@pytest.fixture
def mock_openai_client():
    client = MagicMock(spec=AsyncOpenAI)
    return client


@pytest.fixture
def voice_synthesizer_agent(mock_openai_client):
    config = VoiceSynthesizerConfig(enable_post_processing=False)
    return VoiceSynthesizerAgent(client=mock_openai_client, config=config)


@pytest.fixture
def sample_audio_data():
    return b"fake audio data"


@pytest.mark.asyncio
async def test_synthesize_basic(voice_synthesizer_agent, sample_audio_data):
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    result = await voice_synthesizer_agent.synthesize("Hello world")
    
    assert isinstance(result, str)
    assert os.path.exists(result)
    assert result.endswith('.mp3')
    
    os.unlink(result)
    
    voice_synthesizer_agent.client.audio.speech.create.assert_called_once()


@pytest.mark.asyncio
async def test_synthesize_with_character_info(voice_synthesizer_agent, sample_audio_data):
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    character_info = {
        "appearance": {
            "gender": "female",
            "age": 20
        }
    }
    
    result = await voice_synthesizer_agent.synthesize(
        "Hello", 
        character="小红",
        character_info=character_info
    )
    
    assert os.path.exists(result)
    os.unlink(result)
    
    call_args = voice_synthesizer_agent.client.audio.speech.create.call_args
    assert call_args.kwargs['voice'] == 'nova'


@pytest.mark.asyncio
async def test_synthesize_with_custom_voice(voice_synthesizer_agent, sample_audio_data):
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    result = await voice_synthesizer_agent.synthesize("Hello", voice="shimmer")
    
    assert os.path.exists(result)
    os.unlink(result)
    
    call_args = voice_synthesizer_agent.client.audio.speech.create.call_args
    assert call_args.kwargs['voice'] == 'shimmer'


@pytest.mark.asyncio
async def test_select_voice_male_young(voice_synthesizer_agent):
    character_info = {"appearance": {"gender": "male", "age": 18}}
    voice = voice_synthesizer_agent._select_voice("test", character_info)
    assert voice == "alloy"


@pytest.mark.asyncio
async def test_select_voice_male_adult(voice_synthesizer_agent):
    character_info = {"appearance": {"gender": "male", "age": 30}}
    voice = voice_synthesizer_agent._select_voice("test", character_info)
    assert voice == "onyx"


@pytest.mark.asyncio
async def test_select_voice_female_young(voice_synthesizer_agent):
    character_info = {"appearance": {"gender": "female", "age": 20}}
    voice = voice_synthesizer_agent._select_voice("test", character_info)
    assert voice == "nova"


@pytest.mark.asyncio
async def test_select_voice_female_adult(voice_synthesizer_agent):
    character_info = {"appearance": {"gender": "female", "age": 35}}
    voice = voice_synthesizer_agent._select_voice("test", character_info)
    assert voice == "shimmer"


@pytest.mark.asyncio
async def test_select_voice_narrator(voice_synthesizer_agent):
    voice = voice_synthesizer_agent._select_voice(None, None)
    assert voice == "fable"


@pytest.mark.asyncio
async def test_validate_input_empty(voice_synthesizer_agent):
    with pytest.raises(ValidationError, match="cannot be empty"):
        voice_synthesizer_agent._validate_input("")


@pytest.mark.asyncio
async def test_validate_input_too_long(voice_synthesizer_agent):
    long_text = "a" * 5000
    with pytest.raises(ValidationError, match="too long"):
        voice_synthesizer_agent._validate_input(long_text)


@pytest.mark.asyncio
async def test_call_tts_api_error(voice_synthesizer_agent):
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    with pytest.raises(APIError):
        await voice_synthesizer_agent._call_tts("test", "alloy")


@pytest.mark.asyncio
async def test_generate_batch(voice_synthesizer_agent, sample_audio_data):
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    dialogues = [
        {"text": "Hello", "character": "A"},
        {"text": "World", "character": "B"},
    ]
    
    results = await voice_synthesizer_agent.generate_batch(dialogues)
    
    assert len(results) == 2
    for result in results:
        assert os.path.exists(result)
        os.unlink(result)


@pytest.mark.asyncio
async def test_save_to_temp_error(voice_synthesizer_agent):
    with patch('tempfile.NamedTemporaryFile', side_effect=Exception("File error")):
        with pytest.raises(SynthesisError):
            await voice_synthesizer_agent._save_to_temp(b"test")


@pytest.mark.asyncio
async def test_synthesize_with_post_processing(mock_openai_client, sample_audio_data):
    config = VoiceSynthesizerConfig(enable_post_processing=True)
    agent = VoiceSynthesizerAgent(client=mock_openai_client, config=config)
    
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    with patch.object(agent, '_post_process', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = sample_audio_data
        
        result = await agent.synthesize("Hello")
        
        assert os.path.exists(result)
        os.unlink(result)
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_call_tts_parameters(voice_synthesizer_agent, sample_audio_data):
    mock_response = Mock()
    mock_response.content = sample_audio_data
    
    voice_synthesizer_agent.client.audio.speech.create = AsyncMock(return_value=mock_response)
    
    await voice_synthesizer_agent._call_tts("test text", "alloy")
    
    call_args = voice_synthesizer_agent.client.audio.speech.create.call_args
    assert call_args.kwargs['model'] == 'tts-1'
    assert call_args.kwargs['voice'] == 'alloy'
    assert call_args.kwargs['input'] == 'test text'
    assert call_args.kwargs['speed'] == 1.0
