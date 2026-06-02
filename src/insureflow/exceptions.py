class InsureFlowError(Exception):
    """Base exception for all InsureFlow errors."""
    pass


class ConfigurationError(InsureFlowError):
    """Raised when there is a configuration issue."""
    pass


class DataIngestionError(InsureFlowError):
    """Raised when file or data ingestion fails."""
    pass


class LLMProcessingError(InsureFlowError):
    """Raised when the LLM service fails or returns invalid data."""
    pass


class StorageError(InsureFlowError):
    """Raised when the system fails to read or write to the storage backend."""
    pass