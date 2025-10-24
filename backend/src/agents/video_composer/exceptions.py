class VideoComposerError(Exception):
    pass


class ValidationError(VideoComposerError):
    pass


class CompositionError(VideoComposerError):
    pass


class StorageError(VideoComposerError):
    pass


class DownloadError(VideoComposerError):
    pass
