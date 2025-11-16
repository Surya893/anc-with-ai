"""
Advanced ANC Algorithms - Adaptive Filtering Implementation

Implements advanced noise cancellation algorithms:
1. LMS (Least Mean Squares) adaptive filter
2. NLMS (Normalized LMS) for better convergence
3. RLS (Recursive Least Squares) for optimal performance
4. Frequency-domain adaptive filtering
5. Multi-channel support
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LMSFilter:
    """Least Mean Squares adaptive filter for ANC."""

    def __init__(self, filter_length: int = 512, step_size: float = 0.01):
        """
        Initialize LMS filter.

        Args:
            filter_length: Number of filter taps
            step_size: Learning rate (mu), typically 0.001-0.1
        """
        self.filter_length = filter_length
        self.step_size = step_size
        self.weights = np.zeros(filter_length, dtype=np.float32)
        self.input_buffer = np.zeros(filter_length, dtype=np.float32)

        logger.info(f"LMS Filter initialized: {filter_length} taps, mu={step_size}")

    def update(self, reference: float, desired: float) -> float:
        """
        Update filter with one sample using LMS algorithm.

        Args:
            reference: Reference signal (noise)
            desired: Desired signal (observed signal)

        Returns:
            Anti-noise output
        """
        # Shift input buffer
        self.input_buffer[1:] = self.input_buffer[:-1]
        self.input_buffer[0] = reference

        # Filter output (anti-noise)
        output = np.dot(self.weights, self.input_buffer)

        # Error signal
        error = desired - output

        # Update weights: w(n+1) = w(n) + mu * e(n) * x(n)
        self.weights += self.step_size * error * self.input_buffer

        return output

    def filter_block(self, reference: np.ndarray, desired: np.ndarray) -> np.ndarray:
        """
        Process block of samples.

        Args:
            reference: Reference signal array (noise source)
            desired: Desired signal array (observed signal)

        Returns:
            Anti-noise output array
        """
        output = np.zeros_like(reference)

        for i in range(len(reference)):
            output[i] = self.update(reference[i], desired[i])

        return output

    def reset(self):
        """Reset filter to initial state."""
        self.weights.fill(0)
        self.input_buffer.fill(0)


class NLMSFilter:
    """Normalized LMS filter for improved convergence."""

    def __init__(self, filter_length: int = 512, step_size: float = 0.5,
                 epsilon: float = 1e-6):
        """
        Initialize NLMS filter.

        Args:
            filter_length: Number of filter taps
            step_size: Learning rate (0-2 for stability)
            epsilon: Small constant to avoid division by zero
        """
        self.filter_length = filter_length
        self.step_size = step_size
        self.epsilon = epsilon
        self.weights = np.zeros(filter_length, dtype=np.float32)
        self.input_buffer = np.zeros(filter_length, dtype=np.float32)

        logger.info(f"NLMS Filter initialized: {filter_length} taps, mu={step_size}")

    def update(self, reference: float, desired: float) -> float:
        """
        Update filter using NLMS algorithm.

        Args:
            reference: Reference signal
            desired: Desired signal

        Returns:
            Anti-noise output
        """
        # Shift input buffer
        self.input_buffer[1:] = self.input_buffer[:-1]
        self.input_buffer[0] = reference

        # Filter output
        output = np.dot(self.weights, self.input_buffer)

        # Error signal
        error = desired - output

        # Normalized step size
        power = np.dot(self.input_buffer, self.input_buffer)
        normalized_step = self.step_size / (power + self.epsilon)

        # Update weights: w(n+1) = w(n) + (mu / ||x||^2) * e(n) * x(n)
        self.weights += normalized_step * error * self.input_buffer

        return output

    def filter_block(self, reference: np.ndarray, desired: np.ndarray) -> np.ndarray:
        """Process block of samples."""
        output = np.zeros_like(reference)

        for i in range(len(reference)):
            output[i] = self.update(reference[i], desired[i])

        return output

    def reset(self):
        """Reset filter to initial state."""
        self.weights.fill(0)
        self.input_buffer.fill(0)


class RLSFilter:
    """Recursive Least Squares filter for optimal performance."""

    def __init__(self, filter_length: int = 256, forgetting_factor: float = 0.99,
                 delta: float = 1.0):
        """
        Initialize RLS filter.

        Args:
            filter_length: Number of filter taps
            forgetting_factor: Lambda (0.95-1.0), higher = slower adaptation
            delta: Initial value for inverse correlation matrix
        """
        self.filter_length = filter_length
        self.lambda_ = forgetting_factor
        self.weights = np.zeros(filter_length, dtype=np.float32)
        self.input_buffer = np.zeros(filter_length, dtype=np.float32)

        # Inverse correlation matrix
        self.P = np.eye(filter_length, dtype=np.float32) * delta

        logger.info(f"RLS Filter initialized: {filter_length} taps, lambda={forgetting_factor}")

    def update(self, reference: float, desired: float) -> float:
        """
        Update filter using RLS algorithm.

        Args:
            reference: Reference signal
            desired: Desired signal

        Returns:
            Anti-noise output
        """
        # Shift input buffer
        self.input_buffer[1:] = self.input_buffer[:-1]
        self.input_buffer[0] = reference

        # Filter output
        output = np.dot(self.weights, self.input_buffer)

        # Error signal
        error = desired - output

        # RLS update
        # k(n) = P(n-1) * x(n) / (lambda + x(n)^T * P(n-1) * x(n))
        Px = np.dot(self.P, self.input_buffer)
        denominator = self.lambda_ + np.dot(self.input_buffer, Px)
        gain = Px / denominator

        # Update weights: w(n) = w(n-1) + k(n) * e(n)
        self.weights += gain * error

        # Update P: P(n) = (1/lambda) * (P(n-1) - k(n) * x(n)^T * P(n-1))
        kx = np.outer(gain, self.input_buffer)
        self.P = (self.P - np.dot(kx, self.P)) / self.lambda_

        return output

    def filter_block(self, reference: np.ndarray, desired: np.ndarray) -> np.ndarray:
        """Process block of samples."""
        output = np.zeros_like(reference)

        for i in range(len(reference)):
            output[i] = self.update(reference[i], desired[i])

        return output

    def reset(self):
        """Reset filter to initial state."""
        self.weights.fill(0)
        self.input_buffer.fill(0)
        self.P = np.eye(self.filter_length, dtype=np.float32)


class FrequencyDomainANC:
    """Frequency-domain adaptive noise cancellation."""

    def __init__(self, fft_size: int = 1024, overlap: float = 0.5,
                 step_size: float = 0.1):
        """
        Initialize frequency-domain ANC.

        Args:
            fft_size: FFT size (power of 2)
            overlap: Overlap factor (0-1)
            step_size: Learning rate for frequency bins
        """
        self.fft_size = fft_size
        self.hop_size = int(fft_size * (1 - overlap))
        self.step_size = step_size

        # Frequency-domain weights for each bin
        self.weights = np.ones(fft_size // 2 + 1, dtype=np.complex64)

        # Buffers for overlap-add
        self.input_buffer = np.zeros(fft_size, dtype=np.float32)
        self.output_buffer = np.zeros(fft_size, dtype=np.float32)

        # Window function
        self.window = signal.windows.hann(fft_size, sym=False)

        logger.info(f"Frequency-domain ANC: FFT={fft_size}, overlap={overlap}")

    def process_frame(self, reference: np.ndarray, desired: np.ndarray) -> np.ndarray:
        """
        Process one frame in frequency domain.

        Args:
            reference: Reference signal frame
            desired: Desired signal frame

        Returns:
            Anti-noise output frame
        """
        # Apply window
        ref_windowed = reference * self.window
        des_windowed = desired * self.window

        # FFT
        ref_fft = np.fft.rfft(ref_windowed)
        des_fft = np.fft.rfft(des_windowed)

        # Apply frequency-domain weights
        output_fft = ref_fft * self.weights

        # Error in frequency domain
        error_fft = des_fft - output_fft

        # Update weights: W(k) = W(k) + mu * E(k) * conj(X(k))
        self.weights += self.step_size * error_fft * np.conj(ref_fft)

        # Inverse FFT
        output = np.fft.irfft(output_fft, n=self.fft_size)

        return output

    def process_block(self, reference: np.ndarray, desired: np.ndarray) -> np.ndarray:
        """
        Process block with overlap-add.

        Args:
            reference: Reference signal block
            desired: Desired signal block

        Returns:
            Anti-noise output block
        """
        output = np.zeros_like(reference)

        # Process in overlapping frames
        for i in range(0, len(reference) - self.fft_size + 1, self.hop_size):
            ref_frame = reference[i:i + self.fft_size]
            des_frame = desired[i:i + self.fft_size]

            out_frame = self.process_frame(ref_frame, des_frame)

            # Overlap-add
            output[i:i + self.fft_size] += out_frame

        return output

    def reset(self):
        """Reset filter to initial state."""
        self.weights = np.ones(self.fft_size // 2 + 1, dtype=np.complex64)
        self.input_buffer.fill(0)
        self.output_buffer.fill(0)


class AdaptiveGainController:
    """Adaptive gain control for optimal cancellation."""

    def __init__(self, attack_time: float = 0.01, release_time: float = 0.1,
                 sample_rate: int = 44100):
        """
        Initialize adaptive gain controller.

        Args:
            attack_time: Attack time in seconds
            release_time: Release time in seconds
            sample_rate: Audio sample rate
        """
        self.attack_coef = np.exp(-1.0 / (attack_time * sample_rate))
        self.release_coef = np.exp(-1.0 / (release_time * sample_rate))
        self.envelope = 0.0
        self.target_gain = 1.0
        self.current_gain = 1.0

        logger.info(f"Adaptive gain controller: attack={attack_time}s, release={release_time}s")

    def compute_gain(self, input_level: float, noise_level: float) -> float:
        """
        Compute adaptive gain based on signal levels.

        Args:
            input_level: RMS level of input signal
            noise_level: RMS level of noise estimate

        Returns:
            Adaptive gain factor
        """
        # Compute target gain
        if noise_level > 1e-6:
            self.target_gain = min(input_level / noise_level, 2.0)
        else:
            self.target_gain = 1.0

        # Smooth gain changes
        if self.target_gain > self.current_gain:
            # Attack
            self.current_gain = (self.attack_coef * self.current_gain +
                                (1 - self.attack_coef) * self.target_gain)
        else:
            # Release
            self.current_gain = (self.release_coef * self.current_gain +
                                (1 - self.release_coef) * self.target_gain)

        return self.current_gain

    def process_block(self, anti_noise: np.ndarray,
                     input_signal: np.ndarray,
                     noise_estimate: np.ndarray) -> np.ndarray:
        """
        Apply adaptive gain to anti-noise signal.

        Args:
            anti_noise: Anti-noise signal
            input_signal: Original input signal
            noise_estimate: Estimated noise signal

        Returns:
            Gain-adjusted anti-noise
        """
        # Compute RMS levels
        input_rms = np.sqrt(np.mean(input_signal**2))
        noise_rms = np.sqrt(np.mean(noise_estimate**2))

        # Compute gain
        gain = self.compute_gain(input_rms, noise_rms)

        # Apply gain
        return anti_noise * gain


class MultiChannelANC:
    """Multi-channel ANC for stereo/surround sound."""

    def __init__(self, num_channels: int = 2, filter_type: str = 'nlms',
                 filter_length: int = 512, **filter_kwargs):
        """
        Initialize multi-channel ANC.

        Args:
            num_channels: Number of audio channels
            filter_type: 'lms', 'nlms', or 'rls'
            filter_length: Filter length for each channel
            **filter_kwargs: Additional filter parameters
        """
        self.num_channels = num_channels
        self.filters = []

        # Create filter for each channel
        for i in range(num_channels):
            if filter_type == 'lms':
                filt = LMSFilter(filter_length, **filter_kwargs)
            elif filter_type == 'nlms':
                filt = NLMSFilter(filter_length, **filter_kwargs)
            elif filter_type == 'rls':
                filt = RLSFilter(filter_length, **filter_kwargs)
            else:
                raise ValueError(f"Unknown filter type: {filter_type}")

            self.filters.append(filt)

        logger.info(f"Multi-channel ANC: {num_channels} channels, {filter_type} filters")

    def process_multichannel(self, reference: np.ndarray,
                            desired: np.ndarray) -> np.ndarray:
        """
        Process multi-channel audio.

        Args:
            reference: Reference signals [channels, samples]
            desired: Desired signals [channels, samples]

        Returns:
            Anti-noise outputs [channels, samples]
        """
        if reference.ndim == 1:
            reference = reference.reshape(1, -1)
        if desired.ndim == 1:
            desired = desired.reshape(1, -1)

        output = np.zeros_like(reference)

        # Process each channel independently
        for i in range(self.num_channels):
            output[i] = self.filters[i].filter_block(reference[i], desired[i])

        return output

    def reset(self):
        """Reset all channel filters."""
        for filt in self.filters:
            filt.reset()


class AdvancedANCSystem:
    """Complete advanced ANC system with multiple algorithms."""

    def __init__(self, sample_rate: int = 44100,
                 algorithm: str = 'nlms',
                 filter_length: int = 512,
                 num_channels: int = 1,
                 use_frequency_domain: bool = False,
                 use_adaptive_gain: bool = True):
        """
        Initialize advanced ANC system.

        Args:
            sample_rate: Audio sample rate
            algorithm: 'lms', 'nlms', or 'rls'
            filter_length: Adaptive filter length
            num_channels: Number of audio channels
            use_frequency_domain: Use frequency-domain processing
            use_adaptive_gain: Use adaptive gain control
        """
        self.sample_rate = sample_rate
        self.algorithm = algorithm
        self.num_channels = num_channels

        # Initialize filters
        if use_frequency_domain:
            self.filter = FrequencyDomainANC(fft_size=filter_length * 2)
        elif num_channels > 1:
            self.filter = MultiChannelANC(
                num_channels=num_channels,
                filter_type=algorithm,
                filter_length=filter_length
            )
        else:
            # Single-channel adaptive filter
            if algorithm == 'lms':
                self.filter = LMSFilter(filter_length)
            elif algorithm == 'nlms':
                self.filter = NLMSFilter(filter_length)
            elif algorithm == 'rls':
                self.filter = RLSFilter(filter_length)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")

        # Adaptive gain controller
        self.gain_controller = None
        if use_adaptive_gain:
            self.gain_controller = AdaptiveGainController(sample_rate=sample_rate)

        # Performance metrics
        self.metrics = {
            'mse': [],
            'snr': [],
            'cancellation_db': []
        }

        logger.info(f"Advanced ANC System initialized:")
        logger.info(f"  Algorithm: {algorithm}")
        logger.info(f"  Sample rate: {sample_rate} Hz")
        logger.info(f"  Channels: {num_channels}")
        logger.info(f"  Filter length: {filter_length}")
        logger.info(f"  Frequency domain: {use_frequency_domain}")
        logger.info(f"  Adaptive gain: {use_adaptive_gain}")

    def process(self, reference: np.ndarray, desired: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Process audio through advanced ANC system.

        Args:
            reference: Reference signal (noise source)
            desired: Desired signal (observed signal with noise)

        Returns:
            Tuple of (anti_noise_signal, metrics_dict)
        """
        # Generate anti-noise
        if self.num_channels > 1:
            anti_noise = self.filter.process_multichannel(reference, desired)
        else:
            anti_noise = self.filter.filter_block(reference, desired)

        # Apply adaptive gain
        if self.gain_controller is not None:
            anti_noise = self.gain_controller.process_block(
                anti_noise, desired, reference
            )

        # Compute metrics
        residual = desired - anti_noise
        mse = np.mean(residual**2)

        # SNR improvement
        noise_power = np.mean(desired**2)
        residual_power = np.mean(residual**2)

        if residual_power > 1e-10:
            snr_improvement = 10 * np.log10(noise_power / residual_power)
            cancellation_db = -10 * np.log10(residual_power / noise_power)
        else:
            snr_improvement = 100.0
            cancellation_db = 100.0

        # Update metrics
        metrics = {
            'mse': float(mse),
            'snr_improvement_db': float(snr_improvement),
            'cancellation_db': float(cancellation_db),
            'residual_rms': float(np.sqrt(residual_power))
        }

        self.metrics['mse'].append(mse)
        self.metrics['snr'].append(snr_improvement)
        self.metrics['cancellation_db'].append(cancellation_db)

        return anti_noise, metrics

    def get_performance_summary(self) -> dict:
        """Get summary of performance metrics."""
        if not self.metrics['mse']:
            return {}

        return {
            'avg_mse': float(np.mean(self.metrics['mse'])),
            'avg_snr_improvement_db': float(np.mean(self.metrics['snr'])),
            'avg_cancellation_db': float(np.mean(self.metrics['cancellation_db'])),
            'max_cancellation_db': float(np.max(self.metrics['cancellation_db'])),
            'num_frames_processed': len(self.metrics['mse'])
        }

    def reset(self):
        """Reset system to initial state."""
        self.filter.reset()
        self.metrics = {
            'mse': [],
            'snr': [],
            'cancellation_db': []
        }


if __name__ == "__main__":
    # Test adaptive algorithms
    print("="*80)
    print("ADVANCED ANC ALGORITHMS - TEST")
    print("="*80)

    # Generate test signals
    fs = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(fs * duration))

    # Noise signal (mix of frequencies)
    noise = (0.3 * np.sin(2 * np.pi * 200 * t) +
             0.2 * np.sin(2 * np.pi * 500 * t) +
             0.1 * np.random.randn(len(t)))

    # Reference signal (delayed noise)
    delay_samples = 10
    reference = np.roll(noise, delay_samples)

    # Test each algorithm
    algorithms = ['lms', 'nlms', 'rls']

    for algo in algorithms:
        print(f"\nTesting {algo.upper()} algorithm...")

        anc = AdvancedANCSystem(
            sample_rate=fs,
            algorithm=algo,
            filter_length=256,
            use_adaptive_gain=True
        )

        anti_noise, metrics = anc.process(reference, noise)
        summary = anc.get_performance_summary()

        print(f"  Cancellation: {summary['avg_cancellation_db']:.2f} dB")
        print(f"  SNR improvement: {summary['avg_snr_improvement_db']:.2f} dB")
        print(f"  Residual RMS: {metrics['residual_rms']:.6f}")

    print("\n" + "="*80)
    print("✓ Advanced algorithms tested successfully")
    print("="*80)
