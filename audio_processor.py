"""
Real-time Audio Processing Service
Handles audio streaming, noise cancellation, and classification
"""

import numpy as np
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import base64
import json

from advanced_anc_algorithms import AdvancedANCSystem
from feature_extraction import AudioFeatureExtractor
from predict_sklearn import NoisePredictor
from emergency_noise_detector import EmergencyNoiseDetector


logger = logging.getLogger(__name__)


class AudioProcessor:
    """Real-time audio processing with ANC"""

    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels

        # Initialize components
        self.anc_system = AdvancedANCSystem(
            algorithm='lms',
            sample_rate=sample_rate
        )
        self.feature_extractor = AudioFeatureExtractor(sample_rate=sample_rate)

        try:
            self.noise_predictor = NoisePredictor()
            self.emergency_detector = EmergencyNoiseDetector()
            logger.info("ML models loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")
            self.noise_predictor = None
            self.emergency_detector = None

        # Session state
        self.sessions: Dict[str, 'ProcessingSession'] = {}

        logger.info(f"AudioProcessor initialized: {sample_rate}Hz, {chunk_size} samples, {channels} channels")

    def create_session(self, session_id: str, config: Optional[Dict] = None) -> 'ProcessingSession':
        """Create a new processing session"""
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists, replacing")
            self.end_session(session_id)

        session = ProcessingSession(
            session_id=session_id,
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size,
            config=config or {}
        )

        self.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional['ProcessingSession']:
        """Get existing session"""
        return self.sessions.get(session_id)

    def end_session(self, session_id: str):
        """End and cleanup session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.end()
            del self.sessions[session_id]
            logger.info(f"Ended session: {session_id}")

    async def process_audio_chunk(
        self,
        session_id: str,
        audio_data: np.ndarray,
        apply_anc: bool = True
    ) -> Dict:
        """Process a single audio chunk"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        start_time = datetime.utcnow()

        # Ensure correct shape
        if audio_data.ndim == 1:
            audio_data = audio_data.reshape(-1, 1)

        # Extract features
        features = self.feature_extractor.extract_features(audio_data.flatten())

        # Classify noise
        noise_type = None
        confidence = 0.0
        is_emergency = False

        if self.noise_predictor:
            try:
                noise_type, confidence = self.noise_predictor.predict(audio_data.flatten())
                session.last_noise_type = noise_type
                session.last_confidence = confidence
            except Exception as e:
                logger.error(f"Noise prediction error: {e}")

        if self.emergency_detector and noise_type:
            try:
                is_emergency = self.emergency_detector.is_emergency(noise_type)
            except Exception as e:
                logger.error(f"Emergency detection error: {e}")

        # Apply ANC if enabled
        processed_audio = audio_data.copy()
        cancellation_db = 0.0
        snr_improvement = 0.0

        if apply_anc and session.anc_enabled:
            try:
                # Generate reference signal (in real scenario, from feedforward mic)
                reference = audio_data.flatten()
                desired = audio_data.flatten()

                # Apply ANC
                anti_noise, metrics = self.anc_system.process(reference, desired)

                processed_audio = (desired - anti_noise * session.anc_intensity).reshape(-1, 1)

                cancellation_db = metrics.get('cancellation_db', 0.0)
                snr_improvement = metrics.get('snr_improvement_db', 0.0)

                # Update session metrics
                session.total_cancellation_db += cancellation_db
                session.total_snr_improvement += snr_improvement

            except Exception as e:
                logger.error(f"ANC processing error: {e}")

        # Calculate metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms

        # Update session
        session.chunks_processed += 1
        session.total_latency_ms += processing_time

        # Calculate RMS levels
        original_rms = np.sqrt(np.mean(audio_data ** 2))
        processed_rms = np.sqrt(np.mean(processed_audio ** 2))

        result = {
            'session_id': session_id,
            'chunk_id': session.chunks_processed,
            'timestamp': start_time.isoformat(),

            # Audio data (base64 encoded for transport)
            'original_audio': base64.b64encode(audio_data.tobytes()).decode('utf-8'),
            'processed_audio': base64.b64encode(processed_audio.tobytes()).decode('utf-8'),

            # Features
            'features': {
                'rms': float(features.get('rms', 0)),
                'zero_crossing_rate': float(features.get('zero_crossing_rate', 0)),
                'spectral_centroid': float(features.get('spectral_centroid', 0)),
                'spectral_rolloff': float(features.get('spectral_rolloff', 0))
            },

            # Classification
            'noise_detection': {
                'type': noise_type,
                'confidence': float(confidence),
                'is_emergency': is_emergency
            },

            # ANC metrics
            'anc_metrics': {
                'enabled': session.anc_enabled,
                'intensity': session.anc_intensity,
                'cancellation_db': float(cancellation_db),
                'snr_improvement_db': float(snr_improvement),
                'original_rms': float(original_rms),
                'processed_rms': float(processed_rms),
                'reduction_percent': float((1 - processed_rms / (original_rms + 1e-10)) * 100)
            },

            # Performance
            'performance': {
                'latency_ms': float(processing_time),
                'throughput_chunks_per_sec': float(1000.0 / (processing_time + 1e-10))
            }
        }

        return result

    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get session statistics"""
        session = self.get_session(session_id)
        if not session:
            return None

        return session.get_stats()


class ProcessingSession:
    """Individual processing session state"""

    def __init__(self, session_id: str, sample_rate: int, chunk_size: int, config: Dict):
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.config = config

        # ANC settings
        self.anc_enabled = config.get('anc_enabled', True)
        self.anc_intensity = config.get('anc_intensity', 1.0)
        self.anc_algorithm = config.get('anc_algorithm', 'lms')

        # State
        self.chunks_processed = 0
        self.total_latency_ms = 0.0
        self.total_cancellation_db = 0.0
        self.total_snr_improvement = 0.0

        self.last_noise_type = None
        self.last_confidence = 0.0

        self.started_at = datetime.utcnow()
        self.ended_at = None

    def enable_anc(self, enabled: bool = True):
        """Enable/disable ANC"""
        self.anc_enabled = enabled

    def set_intensity(self, intensity: float):
        """Set ANC intensity (0.0 to 1.0)"""
        self.anc_intensity = max(0.0, min(1.0, intensity))

    def set_algorithm(self, algorithm: str):
        """Set ANC algorithm"""
        self.anc_algorithm = algorithm

    def end(self):
        """End session"""
        self.ended_at = datetime.utcnow()

    def get_stats(self) -> Dict:
        """Get session statistics"""
        duration = (self.ended_at or datetime.utcnow()) - self.started_at
        duration_seconds = duration.total_seconds()

        avg_latency = (
            self.total_latency_ms / self.chunks_processed
            if self.chunks_processed > 0
            else 0.0
        )

        avg_cancellation = (
            self.total_cancellation_db / self.chunks_processed
            if self.chunks_processed > 0
            else 0.0
        )

        avg_snr = (
            self.total_snr_improvement / self.chunks_processed
            if self.chunks_processed > 0
            else 0.0
        )

        return {
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': duration_seconds,
            'anc_enabled': self.anc_enabled,
            'anc_intensity': self.anc_intensity,
            'anc_algorithm': self.anc_algorithm,
            'chunks_processed': self.chunks_processed,
            'average_latency_ms': avg_latency,
            'average_cancellation_db': avg_cancellation,
            'average_snr_improvement_db': avg_snr,
            'last_detection': {
                'type': self.last_noise_type,
                'confidence': self.last_confidence
            }
        }


# Global audio processor instance
audio_processor = AudioProcessor()


# Utility functions for audio data conversion
def audio_bytes_to_numpy(audio_bytes: bytes, dtype='float32') -> np.ndarray:
    """Convert audio bytes to numpy array"""
    return np.frombuffer(audio_bytes, dtype=dtype)


def numpy_to_audio_bytes(audio_array: np.ndarray) -> bytes:
    """Convert numpy array to audio bytes"""
    return audio_array.astype('float32').tobytes()


def audio_base64_to_numpy(audio_b64: str, dtype='float32') -> np.ndarray:
    """Convert base64 audio to numpy array"""
    audio_bytes = base64.b64decode(audio_b64)
    return audio_bytes_to_numpy(audio_bytes, dtype)


def numpy_to_audio_base64(audio_array: np.ndarray) -> str:
    """Convert numpy array to base64 audio"""
    audio_bytes = numpy_to_audio_bytes(audio_array)
    return base64.b64encode(audio_bytes).decode('utf-8')
