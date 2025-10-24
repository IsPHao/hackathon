class VoiceSynthesizerError(Exception):
    pass


class ValidationError(VoiceSynthesizerError):
    pass


class SynthesisError(VoiceSynthesizerError):
    pass


class APIError(VoiceSynthesizerError):
    pass
