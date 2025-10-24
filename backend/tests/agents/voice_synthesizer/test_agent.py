import pytest
import os

from src.agents.voice_synthesizer import (
    VoiceSynthesizerAgent,
    VoiceSynthesizerConfig,
    ValidationError,
    SynthesisError,
    APIError,
)


@pytest.fixture
def agent(fake_audio_client):
    config = VoiceSynthesizerConfig(enable_post_processing=False)
    return VoiceSynthesizerAgent(
        client=fake_audio_client,
        task_id="test-task-123",
        config=config
    )


@pytest.mark.asyncio
async def test_synthesize_basic(agent):
    result = await agent.synthesize("Hello world")
    
    assert isinstance(result, str)
    assert result.endswith('.mp3')
    assert agent.client.call_count == 1


@pytest.mark.asyncio
async def test_synthesize_with_character_info(agent):
    character_info = {
        "appearance": {
            "gender": "female",
            "age": 20
        }
    }
    
    result = await agent.synthesize(
        "Hello", 
        character="小红",
        character_info=character_info
    )
    
    assert isinstance(result, str)
    assert result.endswith('.mp3')
    
    call_args = agent.client.call_history[0]
    assert call_args['voice'] == 'nova'


@pytest.mark.asyncio
async def test_synthesize_with_custom_voice(agent):
    result = await agent.synthesize("Hello", voice="shimmer")
    
    assert isinstance(result, str)
    assert result.endswith('.mp3')
    
    call_args = agent.client.call_history[0]
    assert call_args['voice'] == 'shimmer'


@pytest.mark.asyncio
async def test_select_voice_male_young(agent):
    character_info = {"appearance": {"gender": "male", "age": 18}}
    voice = agent._select_voice("test", character_info)
    assert voice == "alloy"


@pytest.mark.asyncio
async def test_select_voice_male_adult(agent):
    character_info = {"appearance": {"gender": "male", "age": 30}}
    voice = agent._select_voice("test", character_info)
    assert voice == "onyx"


@pytest.mark.asyncio
async def test_select_voice_female_young(agent):
    character_info = {"appearance": {"gender": "female", "age": 20}}
    voice = agent._select_voice("test", character_info)
    assert voice == "nova"


@pytest.mark.asyncio
async def test_select_voice_female_adult(agent):
    character_info = {"appearance": {"gender": "female", "age": 35}}
    voice = agent._select_voice("test", character_info)
    assert voice == "shimmer"


@pytest.mark.asyncio
async def test_select_voice_narrator(agent):
    voice = agent._select_voice(None, None)
    assert voice == "fable"


@pytest.mark.asyncio
async def test_validate_input_empty(agent):
    with pytest.raises(ValidationError, match="cannot be empty"):
        agent._validate_input("")


@pytest.mark.asyncio
async def test_validate_input_too_long(agent):
    long_text = "a" * 5000
    with pytest.raises(ValidationError, match="too long"):
        agent._validate_input(long_text)


@pytest.mark.asyncio
async def test_call_tts_api_error(agent):
    agent.client.set_failure()
    
    with pytest.raises(APIError):
        await agent._call_tts("test", "alloy")


@pytest.mark.asyncio
async def test_generate_batch(agent):
    dialogues = [
        {"text": "Hello", "character": "A"},
        {"text": "World", "character": "B"},
    ]
    
    results = await agent.generate_batch(dialogues)
    
    assert len(results) == 2
    for result in results:
        assert isinstance(result, str)
        assert result.endswith('.mp3')


@pytest.mark.asyncio
async def test_synthesize_with_post_processing(fake_audio_client):
    config = VoiceSynthesizerConfig(enable_post_processing=True)
    agent = VoiceSynthesizerAgent(
        client=fake_audio_client,
        task_id="test-task-123",
        config=config
    )
    
    result = await agent.synthesize("Hello")
    
    assert isinstance(result, str)
    assert result.endswith('.mp3')


@pytest.mark.asyncio
async def test_call_tts_parameters(agent):
    await agent._call_tts("test text", "alloy")
    
    call_args = agent.client.call_history[0]
    assert call_args['model'] == 'tts-1'
    assert call_args['voice'] == 'alloy'
    assert call_args['input'] == 'test text'
    assert call_args['speed'] == 1.0
