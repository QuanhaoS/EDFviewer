"""Domain-specific exceptions for EDFViewer."""


class EDFViewerError(Exception):
    """Base class for user-readable EDFViewer failures."""


class DataLoadError(EDFViewerError):
    """Raised when EDF metadata or signal data cannot be loaded."""


class ParameterValidationError(EDFViewerError):
    """Raised when analysis or display parameters are invalid."""


class PreprocessingError(EDFViewerError):
    """Raised when filtering or downsampling fails."""


class AnalysisError(EDFViewerError):
    """Raised when numerical analysis fails."""


class ExportError(EDFViewerError):
    """Raised when export output cannot be written."""
