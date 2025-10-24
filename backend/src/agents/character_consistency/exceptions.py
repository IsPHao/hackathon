class CharacterConsistencyError(Exception):
    pass


class ValidationError(CharacterConsistencyError):
    pass


class StorageError(CharacterConsistencyError):
    pass


class GenerationError(CharacterConsistencyError):
    pass
