class EstimatorError(Exception):
    """Base exception for estimator errors."""


class ParseError(EstimatorError):
    """Raised when parsing YAML manifests fails fatally."""

