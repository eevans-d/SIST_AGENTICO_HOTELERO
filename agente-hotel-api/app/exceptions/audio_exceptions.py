# audio_exceptions.py


class AudioProcessingError(Exception):
    """
    Base exception for all audio processing errors.
    """

    def __init__(self, message: str, context: dict[str, str] | None = None):
        super().__init__(message)
        self.context = context or {}

    def to_dict(self):
        return {"error": self.__class__.__name__, "message": str(self), "context": self.context}


class AudioDownloadError(AudioProcessingError):
    """
    Raised when audio download fails.
    """

    pass


class AudioConversionError(AudioProcessingError):
    """
    Raised when audio conversion fails.
    """

    pass


class AudioTranscriptionError(AudioProcessingError):
    """
    Raised when audio transcription fails.
    """

    pass


class AudioSynthesisError(AudioProcessingError):
    """
    Raised when audio synthesis fails.
    """

    pass


class AudioTimeoutError(AudioProcessingError):
    """
    Raised when an audio operation times out.
    """

    pass


class AudioValidationError(AudioProcessingError):
    """
    Raised when audio input validation fails.
    """

    pass
