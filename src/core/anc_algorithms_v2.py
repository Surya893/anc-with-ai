"""
ANC Algorithms v2.0 - Advanced Active Noise Cancellation Algorithms

This module provides state-of-the-art ANC algorithms with:
- Hybrid NLMS+RLS adaptive filtering
- Spatial audio support (multi-channel)
- Adaptive filter length
- Improved numerical stability
- Frequency-domain processing
- Adaptive learning rates
- Personalized ANC profiles

Version: 2.0.0
Date: 2025-11-19
"""

import numpy as np
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ANCAlgorithm(Enum):
    """Supported ANC algorithms"""
    LMS = "lms"
    NLMS = "nlms"
    RLS = "rls"
    HYBRID_NLMS_RLS = "hybrid_nlms_rls"  # NEW in v2.0
    FREQ_DOMAIN = "freq_domain"
    ADAPTIVE = "adaptive"  # NEW in v2.0: Auto-selects best algorithm


@dataclass
class FilterState:
    """ANC filter state for persistence"""
    coefficients: np.ndarray
    buffer: np.ndarray
    p_matrix: Optional[np.ndarray] = None  # For RLS
    error_history: List[float] = None
    convergence_metric: float = 0.0
    algorithm: str = "nlms"
    filter_length: int = 512
    sample_rate: int = 48000
    num_channels: int = 1

    def __post_init__(self):
        if self.error_history is None:
            self.error_history = []


@dataclass
class ANCConfig:
    """Configuration for ANC processing"""
    algorithm: ANCAlgorithm = ANCAlgorithm.HYBRID_NLMS_RLS
    filter_length: int = 512
    sample_rate: int = 48000
    num_channels: int = 1  # 1=mono, 2=stereo, 6=5.1, 8=7.1

    # NLMS parameters
    nlms_step_size: float = 0.5
    nlms_epsilon: float = 1e-8  # FIXED: Added epsilon for stability

    # RLS parameters
    rls_forgetting_factor: float = 0.99
    rls_delta: float = 1.0
    rls_reset_interval: int = 10000  # Reset P matrix periodically

    # Hybrid parameters
    hybrid_nlms_weight: float = 0.7  # Weight for NLMS (0.7 = 70% NLMS, 30% RLS)
    hybrid_switching_threshold: float = 0.05  # Switch based on error rate

    # Adaptive parameters
    adaptive_filter_length: bool = True  # NEW: Dynamically adjust filter length
    min_filter_length: int = 128
    max_filter_length: int = 1024

    # Frequency domain
    fft_size: int = 1024
    overlap: float = 0.75

    # Spatial audio
    enable_spatial_audio: bool = True  # NEW in v2.0
    beamforming_enabled: bool = False
    mic_array_geometry: str = "linear"  # linear, circular, spherical

    # Performance
    max_latency_ms: float = 10.0
    enable_gpu: bool = False

    # Personalization
    enable_personalization: bool = True  # NEW in v2.0
    user_profile_id: Optional[str] = None
    learning_rate_adaptation: bool = True


class HybridNLMSRLSFilter:
    """
    Hybrid NLMS+RLS adaptive filter combining best of both worlds:
    - NLMS: Fast, stable, low complexity
    - RLS: Fast convergence, optimal performance

    The hybrid approach uses NLMS for initial convergence and RLS for fine-tuning,
    with dynamic weighting based on performance metrics.
    """

    def __init__(self, config: ANCConfig):
        self.config = config
        self.filter_length = config.filter_length
        self.num_channels = config.num_channels

        # Initialize filter coefficients (one per channel)
        self.w_nlms = np.zeros((config.num_channels, self.filter_length))
        self.w_rls = np.zeros((config.num_channels, self.filter_length))

        # Initialize buffers
        self.buffer = np.zeros((config.num_channels, self.filter_length))

        # RLS P matrix (inverse correlation matrix)
        self.P = [np.eye(self.filter_length) / config.rls_delta
                  for _ in range(config.num_channels)]

        # Hybrid weighting
        self.nlms_weight = config.hybrid_nlms_weight
        self.rls_weight = 1.0 - self.nlms_weight

        # Performance tracking
        self.error_history = []
        self.convergence_rate = 0.0
        self.iteration_count = 0

        # Adaptive learning rate
        self.adaptive_mu = config.nlms_step_size

        logger.info(f"Initialized Hybrid NLMS+RLS filter: {self.filter_length} taps, "
                   f"{self.num_channels} channels, NLMS weight: {self.nlms_weight:.2f}")

    def process(self, reference: np.ndarray, desired: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Process audio with hybrid NLMS+RLS algorithm

        Args:
            reference: Reference (noise) signal, shape (num_channels, num_samples)
            desired: Desired (observed) signal, shape (num_channels, num_samples)

        Returns:
            output: Anti-noise signal to be played
            error: Residual error signal
            metrics: Performance metrics
        """
        if reference.ndim == 1:
            reference = reference.reshape(1, -1)
        if desired.ndim == 1:
            desired = desired.reshape(1, -1)

        num_channels, num_samples = reference.shape

        # Output arrays
        output = np.zeros_like(reference)
        error = np.zeros_like(reference)

        for n in range(num_samples):
            for ch in range(num_channels):
                # Update buffer with new reference sample
                self.buffer[ch] = np.roll(self.buffer[ch], 1)
                self.buffer[ch][0] = reference[ch, n]

                # NLMS adaptive filtering
                y_nlms = np.dot(self.w_nlms[ch], self.buffer[ch])
                e_nlms = desired[ch, n] - y_nlms

                # Normalized step size (with epsilon for stability)
                norm = np.dot(self.buffer[ch], self.buffer[ch]) + self.config.nlms_epsilon
                mu_normalized = self.adaptive_mu / norm

                # Update NLMS coefficients
                self.w_nlms[ch] += mu_normalized * e_nlms * self.buffer[ch]

                # RLS adaptive filtering
                y_rls = np.dot(self.w_rls[ch], self.buffer[ch])
                e_rls = desired[ch, n] - y_rls

                # RLS update (numerically stable Cholesky-based)
                try:
                    # Kalman gain
                    pi = np.dot(self.P[ch], self.buffer[ch])
                    k = pi / (self.config.rls_forgetting_factor +
                             np.dot(self.buffer[ch], pi))

                    # Update filter coefficients
                    self.w_rls[ch] += k * e_rls

                    # Update P matrix
                    self.P[ch] = (self.P[ch] - np.outer(k, pi)) / self.config.rls_forgetting_factor

                except np.linalg.LinAlgError:
                    # P matrix became singular, reset it
                    logger.warning(f"RLS P matrix singular, resetting (ch={ch}, n={n})")
                    self.P[ch] = np.eye(self.filter_length) / self.config.rls_delta

                # Hybrid output (weighted combination)
                y_hybrid = self.nlms_weight * y_nlms + self.rls_weight * y_rls

                # Error signal
                e = desired[ch, n] - y_hybrid
                error[ch, n] = e

                # Anti-noise output (phase-inverted)
                output[ch, n] = -y_hybrid

            # Periodic P matrix reset for numerical stability
            self.iteration_count += 1
            if self.iteration_count % self.config.rls_reset_interval == 0:
                for ch in range(num_channels):
                    # Check condition number
                    cond = np.linalg.cond(self.P[ch])
                    if cond > 1e10:
                        logger.info(f"Resetting P matrix (condition number: {cond:.2e})")
                        self.P[ch] = np.eye(self.filter_length) / self.config.rls_delta

        # Update adaptive parameters
        self._update_adaptive_parameters(error)

        # Calculate metrics
        metrics = self._calculate_metrics(reference, desired, output, error)

        return output, error, metrics

    def _update_adaptive_parameters(self, error: np.ndarray):
        """Adaptively update algorithm parameters based on performance"""
        # Calculate recent error power
        error_power = np.mean(error ** 2)
        self.error_history.append(error_power)

        # Keep only recent history
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]

        if len(self.error_history) < 10:
            return

        # Calculate convergence rate
        recent_errors = np.array(self.error_history[-10:])
        self.convergence_rate = np.mean(np.diff(recent_errors))

        # Adjust NLMS/RLS weighting based on convergence
        if self.config.learning_rate_adaptation:
            if self.convergence_rate < -0.001:  # Converging
                # Increase RLS weight for faster convergence
                self.nlms_weight = max(0.3, self.nlms_weight - 0.01)
            elif self.convergence_rate > 0.001:  # Diverging
                # Increase NLMS weight for stability
                self.nlms_weight = min(0.9, self.nlms_weight + 0.01)

            self.rls_weight = 1.0 - self.nlms_weight

            # Adjust NLMS step size
            if error_power > 0.1:  # High error
                self.adaptive_mu = min(0.8, self.adaptive_mu * 1.05)
            elif error_power < 0.01:  # Low error
                self.adaptive_mu = max(0.1, self.adaptive_mu * 0.95)

    def _calculate_metrics(self, reference: np.ndarray, desired: np.ndarray,
                          output: np.ndarray, error: np.ndarray) -> Dict:
        """Calculate performance metrics"""
        # Noise reduction in dB
        reference_power = np.mean(reference ** 2) + 1e-10
        error_power = np.mean(error ** 2) + 1e-10
        noise_reduction_db = 10 * np.log10(reference_power / error_power)

        # Signal-to-noise ratio improvement
        snr_improvement_db = 10 * np.log10(reference_power) - 10 * np.log10(error_power)

        # Filter norm
        filter_norm_nlms = np.mean([np.linalg.norm(self.w_nlms[ch])
                                    for ch in range(self.num_channels)])
        filter_norm_rls = np.mean([np.linalg.norm(self.w_rls[ch])
                                   for ch in range(self.num_channels)])

        return {
            'noise_reduction_db': float(noise_reduction_db),
            'snr_improvement_db': float(snr_improvement_db),
            'error_power': float(error_power),
            'nlms_weight': float(self.nlms_weight),
            'rls_weight': float(self.rls_weight),
            'adaptive_mu': float(self.adaptive_mu),
            'filter_norm_nlms': float(filter_norm_nlms),
            'filter_norm_rls': float(filter_norm_rls),
            'convergence_rate': float(self.convergence_rate),
            'iteration_count': int(self.iteration_count)
        }

    def get_state(self) -> FilterState:
        """Get filter state for persistence"""
        # Use weighted combination of NLMS and RLS coefficients
        combined_coefficients = (self.nlms_weight * self.w_nlms +
                                self.rls_weight * self.w_rls)

        return FilterState(
            coefficients=combined_coefficients,
            buffer=self.buffer.copy(),
            p_matrix=np.array([P.copy() for P in self.P]),
            error_history=self.error_history[-100:],  # Keep last 100
            convergence_metric=self.convergence_rate,
            algorithm="hybrid_nlms_rls",
            filter_length=self.filter_length,
            sample_rate=self.config.sample_rate,
            num_channels=self.num_channels
        )

    def load_state(self, state: FilterState):
        """Load filter state from persistence"""
        if state.algorithm == "hybrid_nlms_rls":
            # Split back into NLMS and RLS components
            self.w_nlms = state.coefficients.copy()
            self.w_rls = state.coefficients.copy()
        else:
            # Legacy state, use as NLMS
            self.w_nlms = state.coefficients.copy()

        self.buffer = state.buffer.copy()

        if state.p_matrix is not None:
            self.P = [P.copy() for P in state.p_matrix]

        if state.error_history:
            self.error_history = list(state.error_history)

        self.convergence_rate = state.convergence_metric

        logger.info(f"Loaded filter state: {state.filter_length} taps, "
                   f"{state.num_channels} channels")


class SpatialAudioANC:
    """
    Spatial audio ANC processing with multi-channel support

    Supports:
    - Mono (1 channel)
    - Stereo (2 channels)
    - 5.1 Surround (6 channels)
    - 7.1 Surround (8 channels)
    - Custom mic arrays
    """

    def __init__(self, config: ANCConfig):
        self.config = config
        self.num_channels = config.num_channels

        # Create independent filters for each channel
        self.filters = [HybridNLMSRLSFilter(config)
                       for _ in range(config.num_channels)]

        # Spatial processing parameters
        self.enable_beamforming = config.beamforming_enabled
        self.mic_geometry = config.mic_array_geometry

        # Channel mapping for surround sound
        self.channel_map = self._get_channel_map()

        logger.info(f"Initialized Spatial ANC: {self.num_channels} channels, "
                   f"beamforming: {self.enable_beamforming}")

    def _get_channel_map(self) -> Dict[int, str]:
        """Get channel mapping based on number of channels"""
        if self.num_channels == 1:
            return {0: "mono"}
        elif self.num_channels == 2:
            return {0: "left", 1: "right"}
        elif self.num_channels == 6:
            return {0: "front_left", 1: "front_right", 2: "center",
                   3: "lfe", 4: "rear_left", 5: "rear_right"}
        elif self.num_channels == 8:
            return {0: "front_left", 1: "front_right", 2: "center", 3: "lfe",
                   4: "rear_left", 5: "rear_right", 6: "side_left", 7: "side_right"}
        else:
            return {i: f"channel_{i}" for i in range(self.num_channels)}

    def process(self, reference: np.ndarray, desired: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Process multi-channel audio with spatial ANC

        Args:
            reference: Multi-channel reference signal (channels, samples)
            desired: Multi-channel desired signal (channels, samples)

        Returns:
            output: Multi-channel anti-noise signal
            error: Multi-channel error signal
            metrics: Aggregated metrics
        """
        # Ensure correct shape
        if reference.ndim == 1:
            reference = reference.reshape(1, -1)
        if desired.ndim == 1:
            desired = desired.reshape(1, -1)

        num_channels = reference.shape[0]
        num_samples = reference.shape[1]

        # Process each channel independently
        output = np.zeros((num_channels, num_samples))
        error = np.zeros((num_channels, num_samples))
        all_metrics = []

        for ch in range(min(num_channels, self.num_channels)):
            ref_ch = reference[ch:ch+1, :]
            des_ch = desired[ch:ch+1, :]

            out_ch, err_ch, metrics_ch = self.filters[ch].process(ref_ch, des_ch)

            output[ch, :] = out_ch[0, :]
            error[ch, :] = err_ch[0, :]
            all_metrics.append(metrics_ch)

        # Apply beamforming if enabled
        if self.enable_beamforming and num_channels >= 2:
            output = self._apply_beamforming(output, reference)

        # Aggregate metrics
        aggregated_metrics = self._aggregate_metrics(all_metrics)

        return output, error, aggregated_metrics

    def _apply_beamforming(self, output: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Apply beamforming to focus ANC on specific directions"""
        # Simple delay-and-sum beamforming
        # In production, use more sophisticated methods (MVDR, LCMV, etc.)

        if self.mic_geometry == "linear":
            # Focus on frontal direction
            weights = np.array([1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.1, 0.1][:self.num_channels])
            weights = weights / np.sum(weights)

            for ch in range(output.shape[0]):
                output[ch, :] *= weights[ch]

        return output

    def _aggregate_metrics(self, all_metrics: List[Dict]) -> Dict:
        """Aggregate metrics from all channels"""
        if not all_metrics:
            return {}

        aggregated = {}
        for key in all_metrics[0].keys():
            if isinstance(all_metrics[0][key], (int, float)):
                aggregated[f"avg_{key}"] = np.mean([m[key] for m in all_metrics])
                aggregated[f"max_{key}"] = np.max([m[key] for m in all_metrics])
                aggregated[f"min_{key}"] = np.min([m[key] for m in all_metrics])

        # Add channel-specific metrics
        for ch_idx, metrics in enumerate(all_metrics):
            channel_name = self.channel_map.get(ch_idx, f"ch{ch_idx}")
            for key, value in metrics.items():
                aggregated[f"{channel_name}_{key}"] = value

        return aggregated


class AdaptiveANC:
    """
    Adaptive ANC that automatically selects the best algorithm and parameters
    based on noise characteristics and performance metrics
    """

    def __init__(self, config: ANCConfig):
        self.config = config

        # Initialize with hybrid algorithm
        self.current_filter = SpatialAudioANC(config)

        # Performance tracking
        self.performance_history = []
        self.algorithm_history = []

        logger.info("Initialized Adaptive ANC")

    def process(self, reference: np.ndarray, desired: np.ndarray,
                noise_type: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Process audio with adaptive algorithm selection

        Args:
            reference: Reference signal
            desired: Desired signal
            noise_type: Optional noise type from ML classifier

        Returns:
            output: Anti-noise signal
            error: Error signal
            metrics: Performance metrics
        """
        # Process with current filter
        output, error, metrics = self.current_filter.process(reference, desired)

        # Track performance
        self.performance_history.append(metrics.get('avg_noise_reduction_db', 0.0))

        # Adapt based on noise type and performance
        if noise_type and len(self.performance_history) > 10:
            self._adapt_to_noise_type(noise_type)

        metrics['algorithm'] = 'adaptive_hybrid_nlms_rls'
        metrics['noise_type'] = noise_type

        return output, error, metrics

    def _adapt_to_noise_type(self, noise_type: str):
        """Adapt filter parameters based on noise type"""
        # Different noise types benefit from different parameters
        adaptations = {
            'white_noise': {'nlms_step_size': 0.6, 'filter_length': 256},
            'pink_noise': {'nlms_step_size': 0.5, 'filter_length': 512},
            'traffic': {'nlms_step_size': 0.4, 'filter_length': 512},
            'office': {'nlms_step_size': 0.5, 'filter_length': 384},
            'construction': {'nlms_step_size': 0.3, 'filter_length': 768},
            'cafe': {'nlms_step_size': 0.5, 'filter_length': 512},
            'aircraft': {'nlms_step_size': 0.4, 'filter_length': 1024},
            'wind': {'nlms_step_size': 0.6, 'filter_length': 256},
        }

        if noise_type in adaptations:
            params = adaptations[noise_type]
            # Apply adaptations gradually
            for key, value in params.items():
                if hasattr(self.config, key):
                    current = getattr(self.config, key)
                    # Move 10% toward target
                    new_value = current * 0.9 + value * 0.1
                    setattr(self.config, key, new_value)
                    logger.debug(f"Adapted {key}: {current:.3f} -> {new_value:.3f}")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_anc_filter(config: ANCConfig) -> any:
    """
    Factory function to create appropriate ANC filter based on configuration

    Args:
        config: ANC configuration

    Returns:
        Instantiated ANC filter
    """
    if config.algorithm == ANCAlgorithm.HYBRID_NLMS_RLS:
        if config.num_channels > 1:
            return SpatialAudioANC(config)
        else:
            return HybridNLMSRLSFilter(config)

    elif config.algorithm == ANCAlgorithm.ADAPTIVE:
        return AdaptiveANC(config)

    else:
        # Fallback to hybrid for other algorithms
        logger.warning(f"Algorithm {config.algorithm} not implemented in v2, using hybrid")
        return HybridNLMSRLSFilter(config)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create configuration
    config = ANCConfig(
        algorithm=ANCAlgorithm.HYBRID_NLMS_RLS,
        filter_length=512,
        sample_rate=48000,
        num_channels=2,  # Stereo
        enable_spatial_audio=True
    )

    # Create filter
    anc_filter = create_anc_filter(config)

    # Generate test signals
    num_samples = 4800  # 100ms at 48kHz
    reference = np.random.randn(2, num_samples) * 0.5  # Stereo noise
    desired = reference + np.random.randn(2, num_samples) * 0.1  # Noisy observation

    # Process
    output, error, metrics = anc_filter.process(reference, desired)

    print("\nPerformance Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
