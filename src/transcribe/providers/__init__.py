"""Multi-provider transcription interface for vision language models."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from enum import Enum


class ProviderType(Enum):
    """Types of vision model providers."""
    API_BASED = "api"
    LOCAL = "local"
    CLOUD = "cloud"


class ModelCapability(Enum):
    """Model capabilities for different use cases."""
    OCR = "ocr"
    HANDWRITING = "handwriting"
    STRUCTURED_OUTPUT = "structured"
    MULTILINGUAL = "multilingual"
    LONG_CONTEXT = "long_context"


@dataclass
class TranscriptionResult:
    """Result from a transcription operation."""
    success: bool
    text: str
    confidence: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    cost: Optional[float] = None
    tokens_used: Optional[int] = None


@dataclass
class CostEstimate:
    """Cost estimation for transcription."""
    estimated_cost: float
    cost_per_page: float
    total_pages: int
    model_name: str
    currency: str = "USD"
    notes: Optional[str] = None


@dataclass
class ModelInfo:
    """Information about a vision model."""
    name: str
    provider: str
    model_id: str
    max_tokens: int
    supports_batch: bool
    cost_per_image: Optional[float] = None
    capabilities: List[ModelCapability] = None
    context_window: Optional[int] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class VisionProviderError(Exception):
    """Base exception for vision provider errors."""
    pass


class ModelNotAvailableError(VisionProviderError):
    """Raised when a requested model is not available."""
    pass


class AuthenticationError(VisionProviderError):
    """Raised when authentication fails."""
    pass


class RateLimitError(VisionProviderError):
    """Raised when rate limits are exceeded."""
    pass


class InsufficientCreditsError(VisionProviderError):
    """Raised when account has insufficient credits."""
    pass


class VisionProvider(abc.ABC):
    """Abstract base class for vision language model providers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_type = self._get_provider_type()

    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """Return the type of this provider."""
        pass

    @abc.abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models for this provider."""
        pass

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is available and configured correctly."""
        pass

    @abc.abstractmethod
    def estimate_cost(self, num_pages: int, model_name: str) -> CostEstimate:
        """Estimate cost for transcribing given number of pages."""
        pass

    @abc.abstractmethod
    def transcribe_image(
        self,
        image_path: Path,
        model_name: str,
        prompt: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe a single image to text.

        Args:
            image_path: Path to image file
            model_name: Model identifier to use
            prompt: Optional custom prompt
            **kwargs: Provider-specific options

        Returns:
            TranscriptionResult with text and metadata
        """
        pass

    @abc.abstractmethod
    def transcribe_batch(
        self,
        image_paths: List[Path],
        model_name: str,
        prompt: Optional[str] = None,
        **kwargs
    ) -> List[TranscriptionResult]:
        """Transcribe multiple images in batch (if supported).

        Args:
            image_paths: List of image file paths
            model_name: Model identifier to use
            prompt: Optional custom prompt
            **kwargs: Provider-specific options

        Returns:
            List of TranscriptionResult objects
        """
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of the provider."""
        pass

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Default model name for this provider."""
        pass

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        models = self.get_available_models()
        return next((m for m in models if m.model_id == model_name), None)

    def supports_capability(self, model_name: str, capability: ModelCapability) -> bool:
        """Check if a model supports a specific capability."""
        model = self.get_model_info(model_name)
        return model is not None and capability in model.capabilities
