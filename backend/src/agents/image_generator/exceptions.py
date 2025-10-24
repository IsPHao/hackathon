class ImageGeneratorError(Exception):
    pass


class ValidationError(ImageGeneratorError):
    pass


class GenerationError(ImageGeneratorError):
    pass


class StorageError(ImageGeneratorError):
    pass


class APIError(ImageGeneratorError):
    pass
