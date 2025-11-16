"""
Production Audio Processing Engine
Real-time audio capture, processing, and playback with <30ms latency
"""

import numpy as np
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple, Callable
import queue
import threading
from collections import deque

from advanced_anc_algorithms import AdvancedANCSystem, LMSFilter, NLMSFilter, RLSFilter
from feature_extraction import AudioFeatureExtractor
from predict_sklearn import NoisePredictor
from emergency_noise_detector import EmergencyNoiseDetector


logger = logging.getLogger(__name__)


class RealTimeAudioProcessor:
    """
    Production-grade real-time audio processor with hardware integration
    Designed for <30ms latency with real microphone and speaker output
    """

    def __init__(
        self,
        sample_rate: int = 48000,  # 48kHz for better quality
        chunk_size: int = 512,     # Smaller chunks for lower latency
        channels: int = 1,
        buffer_size: int = 3       # Number of chunks to buffer
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.buffer_size = buffer_size

        # Processing components
        self.anc_system = AdvancedANCSystem(
            algorithm='nlms',  # NLMS for better stability
            sample_rate=sample_rate
        )

        # ML models (optional, can disable for lower latency)
        try:
            self.feature_extractor = AudioFeatureExtractor(sample_rate=sample_rate)
            self.noise_predictor = NoisePredictor()
            self.emergency_detector = EmergencyNoiseDetector()
            self.ml_enabled = True
        except Exception as e:
            logger.warning(f"ML models not available: {e}")
            self.ml_enabled = False

        # Audio buffers - use thread-safe queues
        self.input_buffer = queue.Queue(maxsize=buffer_size)
        self.output_buffer = queue.Queue(maxsize=buffer_size)

        # Processing state
        self.is_processing = False
        self.anc_enabled = True
        self.anc_intensity = 1.0
        self.bypass_ml = False  # Set to True for minimum latency

        # Performance metrics
        self.total_chunks = 0
        self.total_latency_ms = 0
        self.dropped_chunks = 0

        # Reference signal buffer (for feedforward ANC)
        self.reference_buffer = deque(maxlen=self.chunk_size * 2)

        logger.info(f"RealTimeAudioProcessor initialized: {sample_rate}Hz, {chunk_size} samples")

    def start_processing(self):
        """Start real-time audio processing"""
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        logger.info("Real-time processing started")

    def stop_processing(self):
        """Stop real-time audio processing"""
        self.is_processing = False
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join(timeout=1.0)
        logger.info("Real-time processing stopped")

    def process_chunk(self, audio_chunk: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Process a single audio chunk with minimum latency

        Args:
            audio_chunk: Input audio (shape: [chunk_size] or [chunk_size, channels])

        Returns:
            Tuple of (processed_audio, metrics)
        """
        start_time = datetime.utcnow()

        # Ensure correct shape
        if audio_chunk.ndim == 1:
            audio_chunk = audio_chunk.reshape(-1, 1)

        # Add to reference buffer
        self.reference_buffer.extend(audio_chunk.flatten())

        # Get reference signal (past audio for feedforward)
        if len(self.reference_buffer) >= self.chunk_size:
            reference = np.array(list(self.reference_buffer)[-self.chunk_size:])
        else:
            reference = np.zeros(self.chunk_size)

        # Apply ANC if enabled
        if self.anc_enabled:
            try:
                # Use NLMS for stability
                desired = audio_chunk.flatten()
                anti_noise, anc_metrics = self.anc_system.process(reference, desired)

                # Apply intensity scaling
                processed = desired - (anti_noise * self.anc_intensity)

                cancellation_db = anc_metrics.get('cancellation_db', 0.0)

            except Exception as e:
                logger.error(f"ANC processing error: {e}")
                processed = audio_chunk.flatten()
                cancellation_db = 0.0
        else:
            processed = audio_chunk.flatten()
            cancellation_db = 0.0

        # Optional ML classification (can be bypassed for lower latency)
        noise_type = None
        confidence = 0.0
        is_emergency = False

        if self.ml_enabled and not self.bypass_ml and self.total_chunks % 10 == 0:
            # Only classify every 10th chunk to reduce CPU load
            try:
                noise_type, confidence = self.noise_predictor.predict(audio_chunk.flatten())
                is_emergency = self.emergency_detector.is_emergency(noise_type)
            except Exception as e:
                logger.debug(f"ML classification skipped: {e}")

        # Calculate latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update metrics
        self.total_chunks += 1
        self.total_latency_ms += latency_ms

        # Reshape output
        processed = processed.reshape(-1, self.channels)

        metrics = {
            'chunk_id': self.total_chunks,
            'latency_ms': latency_ms,
            'cancellation_db': cancellation_db,
            'noise_type': noise_type,
            'confidence': confidence,
            'is_emergency': is_emergency,
            'avg_latency_ms': self.total_latency_ms / self.total_chunks if self.total_chunks > 0 else 0
        }

        return processed, metrics

    def _processing_loop(self):
        """Background processing loop for continuous audio stream"""
        logger.info("Processing loop started")

        while self.is_processing:
            try:
                # Get input chunk (with timeout to allow checking is_processing)
                try:
                    input_chunk = self.input_buffer.get(timeout=0.01)
                except queue.Empty:
                    continue

                # Process
                processed_chunk, metrics = self.process_chunk(input_chunk)

                # Put output chunk
                try:
                    self.output_buffer.put(processed_chunk, block=False)
                except queue.Full:
                    self.dropped_chunks += 1
                    logger.warning(f"Output buffer full, dropped chunk (total: {self.dropped_chunks})")

            except Exception as e:
                logger.error(f"Processing loop error: {e}", exc_info=True)

        logger.info("Processing loop stopped")

    def put_input_chunk(self, audio_chunk: np.ndarray) -> bool:
        """
        Add audio chunk to input buffer

        Returns:
            True if successful, False if buffer is full
        """
        try:
            self.input_buffer.put(audio_chunk, block=False)
            return True
        except queue.Full:
            self.dropped_chunks += 1
            return False

    def get_output_chunk(self, timeout: float = 0.01) -> Optional[np.ndarray]:
        """
        Get processed audio chunk from output buffer

        Args:
            timeout: Maximum time to wait for chunk

        Returns:
            Processed audio chunk or None if timeout
        """
        try:
            return self.output_buffer.get(timeout=timeout)
        except queue.Empty:
            return None

    def set_anc_enabled(self, enabled: bool):
        """Enable/disable ANC processing"""
        self.anc_enabled = enabled
        logger.info(f"ANC {'enabled' if enabled else 'disabled'}")

    def set_anc_intensity(self, intensity: float):
        """Set ANC intensity (0.0 to 1.0)"""
        self.anc_intensity = max(0.0, min(1.0, intensity))
        logger.info(f"ANC intensity set to {self.anc_intensity}")

    def set_algorithm(self, algorithm: str):
        """Change ANC algorithm"""
        self.anc_system = AdvancedANCSystem(
            algorithm=algorithm,
            sample_rate=self.sample_rate
        )
        logger.info(f"ANC algorithm changed to {algorithm}")

    def set_bypass_ml(self, bypass: bool):
        """Bypass ML for minimum latency"""
        self.bypass_ml = bypass
        logger.info(f"ML classification {'bypassed' if bypass else 'enabled'}")

    def get_stats(self) -> dict:
        """Get processing statistics"""
        return {
            'total_chunks': self.total_chunks,
            'avg_latency_ms': self.total_latency_ms / self.total_chunks if self.total_chunks > 0 else 0,
            'dropped_chunks': self.dropped_chunks,
            'input_buffer_size': self.input_buffer.qsize(),
            'output_buffer_size': self.output_buffer.qsize(),
            'anc_enabled': self.anc_enabled,
            'anc_intensity': self.anc_intensity,
            'ml_enabled': self.ml_enabled and not self.bypass_ml
        }

    def reset_stats(self):
        """Reset processing statistics"""
        self.total_chunks = 0
        self.total_latency_ms = 0
        self.dropped_chunks = 0
        logger.info("Statistics reset")


class StreamingAudioSession:
    """
    Manages a streaming audio session with a client
    Handles audio flow: mic → processing → speakers
    """

    def __init__(
        self,
        session_id: str,
        sample_rate: int = 48000,
        chunk_size: int = 512,
        **config
    ):
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # Create processor
        self.processor = RealTimeAudioProcessor(
            sample_rate=sample_rate,
            chunk_size=chunk_size,
            channels=config.get('channels', 1),
            buffer_size=config.get('buffer_size', 3)
        )

        # Session state
        self.is_active = False
        self.started_at = datetime.utcnow()
        self.last_activity = self.started_at

        # Configuration
        self.processor.set_anc_enabled(config.get('anc_enabled', True))
        self.processor.set_anc_intensity(config.get('anc_intensity', 1.0))
        if 'anc_algorithm' in config:
            self.processor.set_algorithm(config['anc_algorithm'])
        if 'bypass_ml' in config:
            self.processor.set_bypass_ml(config['bypass_ml'])

        logger.info(f"Streaming session created: {session_id}")

    def start(self):
        """Start streaming session"""
        self.is_active = True
        self.processor.start_processing()
        logger.info(f"Session started: {self.session_id}")

    def stop(self):
        """Stop streaming session"""
        self.is_active = False
        self.processor.stop_processing()
        logger.info(f"Session stopped: {self.session_id}")

    def process_audio_chunk(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Process audio chunk and return processed audio

        Args:
            audio_data: Input audio chunk

        Returns:
            Processed audio chunk or None if processing failed
        """
        self.last_activity = datetime.utcnow()

        # Add to input buffer
        if not self.processor.put_input_chunk(audio_data):
            logger.warning(f"Input buffer full for session {self.session_id}")
            return None

        # Get processed output
        processed = self.processor.get_output_chunk(timeout=0.05)
        return processed

    def get_stats(self) -> dict:
        """Get session statistics"""
        stats = self.processor.get_stats()
        stats.update({
            'session_id': self.session_id,
            'is_active': self.is_active,
            'started_at': self.started_at.isoformat(),
            'duration_seconds': (datetime.utcnow() - self.started_at).total_seconds(),
            'last_activity': self.last_activity.isoformat()
        })
        return stats

    def update_settings(self, **settings):
        """Update processing settings"""
        if 'anc_enabled' in settings:
            self.processor.set_anc_enabled(settings['anc_enabled'])
        if 'anc_intensity' in settings:
            self.processor.set_anc_intensity(settings['anc_intensity'])
        if 'anc_algorithm' in settings:
            self.processor.set_algorithm(settings['anc_algorithm'])
        if 'bypass_ml' in settings:
            self.processor.set_bypass_ml(settings['bypass_ml'])


# Global session manager
streaming_sessions = {}


def create_streaming_session(session_id: str, **config) -> StreamingAudioSession:
    """Create a new streaming audio session"""
    if session_id in streaming_sessions:
        # Close existing session
        streaming_sessions[session_id].stop()
        del streaming_sessions[session_id]

    session = StreamingAudioSession(session_id, **config)
    streaming_sessions[session_id] = session
    return session


def get_streaming_session(session_id: str) -> Optional[StreamingAudioSession]:
    """Get existing streaming session"""
    return streaming_sessions.get(session_id)


def end_streaming_session(session_id: str):
    """End and cleanup streaming session"""
    if session_id in streaming_sessions:
        streaming_sessions[session_id].stop()
        del streaming_sessions[session_id]
        logger.info(f"Session ended and cleaned up: {session_id}")
