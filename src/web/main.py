#!/usr/bin/env python3
"""
Active Noise Cancellation System - Main Integration Script

Integrates all components:
1. Sound Receiver - Real-time audio capture
2. Analysis - Feature extraction, intensity, classification
3. Model Builder - Training and prediction
4. Releaser - Anti-noise generation and output
5. UI Interaction - Flask web interface
"""

import os
import sys
import time
import threading
import queue
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path

# Import required modules
from database_schema import ANCDatabase
from feature_extraction import AudioFeatureExtractor
from predict_sklearn import NoisePredictor
from emergency_noise_detector import EmergencyNoiseDetector
from anti_noise_generator import AntiNoiseGenerator
import librosa

# Try to import PyAudio (optional for testing without hardware)
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("Warning: PyAudio not available. Audio I/O will be disabled.")


class ANCSystemCore:
    """Core ANC system integrating all components."""

    def __init__(self,
                 db_path="anc_system.db",
                 model_path="models/noise_classifier_sklearn.joblib",
                 scaler_path="models/scaler_sklearn.joblib",
                 emergency_model_path="models/emergency_classifier.joblib",
                 sample_rate=44100,
                 chunk_size=1024,
                 channels=1):
        """Initialize ANC system core."""

        print("="*80)
        print("INITIALIZING ACTIVE NOISE CANCELLATION SYSTEM")
        print("="*80)

        # Audio parameters
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None

        # Database
        print("\n[1/7] Connecting to database...")
        self.db = ANCDatabase(db_path)
        print(f"✓ Database connected: {db_path}")

        # Feature extraction
        print("\n[2/7] Initializing feature extractor...")
        self.feature_extractor = AudioFeatureExtractor(sample_rate=sample_rate)
        print("✓ Feature extractor ready")

        # Noise classifier
        print("\n[3/7] Loading noise classifier...")
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.noise_predictor = NoisePredictor(
                model_path=model_path,
                scaler_path=scaler_path
            )
            print(f"✓ Classifier loaded: {model_path}")
        else:
            print(f"⚠ Classifier not found: {model_path}")
            print("  Run train_sklearn_demo.py to train the model first")
            self.noise_predictor = None

        # Emergency detector
        print("\n[4/7] Loading emergency detector...")
        if os.path.exists(emergency_model_path):
            self.emergency_detector = EmergencyNoiseDetector(
                model_path=emergency_model_path
            )
            print(f"✓ Emergency detector loaded: {emergency_model_path}")
        else:
            print(f"⚠ Emergency detector not found: {emergency_model_path}")
            print("  Emergency detection will be disabled")
            self.emergency_detector = None

        # Anti-noise generator
        print("\n[5/7] Initializing anti-noise generator...")
        self.anti_noise_gen = AntiNoiseGenerator(
            sample_rate=sample_rate,
            emergency_detector=self.emergency_detector
        )
        print("✓ Anti-noise generator ready")

        # PyAudio
        print("\n[6/7] Initializing audio interface...")
        if PYAUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
            print("✓ PyAudio initialized")
        else:
            self.audio = None
            print("⚠ PyAudio not available - audio I/O disabled")

        # System state
        print("\n[7/7] Setting up system state...")
        self.running = False
        self.anc_enabled = False
        self.noise_intensity_threshold = 0.5
        self.audio_queue = queue.Queue(maxsize=100)
        self.state_lock = threading.Lock()

        # Current state
        self.current_noise_class = "unknown"
        self.current_confidence = 0.0
        self.current_intensity = 0.0
        self.emergency_detected = False
        self.emergency_bypass = False

        # Statistics
        self.stats = {
            'total_detections': 0,
            'emergency_count': 0,
            'anc_active_time': 0,
            'start_time': None
        }

        print("✓ System state initialized")
        print("\n" + "="*80)
        print("ANC SYSTEM READY")
        print("="*80)

    def analyze_audio(self, audio_data):
        """Analyze audio and classify noise type."""

        # Extract features
        features = self.feature_extractor.extract_feature_vector(audio_data)

        # Calculate intensity (dB)
        rms = np.sqrt(np.mean(audio_data**2))
        intensity_db = 20 * np.log10(rms + 1e-10)

        # Classify noise
        noise_class = "unknown"
        confidence = 0.0

        if self.noise_predictor:
            try:
                noise_class, confidence, _ = self.noise_predictor.predict(features)

                with self.state_lock:
                    self.stats['total_detections'] += 1

            except Exception as e:
                print(f"Classification error: {e}")

        # Check for emergency
        is_emergency = False
        if self.emergency_detector:
            try:
                is_emergency = self.emergency_detector.detect_emergency(audio_data)
                if is_emergency:
                    with self.state_lock:
                        self.stats['emergency_count'] += 1
                        self.emergency_detected = True
                        self.emergency_bypass = True
            except Exception as e:
                print(f"Emergency detection error: {e}")

        return {
            'noise_class': noise_class,
            'confidence': confidence,
            'intensity_db': intensity_db,
            'is_emergency': is_emergency,
            'features': features
        }

    def process_audio_chunk(self, audio_data):
        """Process single audio chunk through complete pipeline."""

        # Analyze audio
        analysis = self.analyze_audio(audio_data)

        # Update current state
        with self.state_lock:
            self.current_noise_class = analysis['noise_class']
            self.current_confidence = analysis['confidence']
            self.current_intensity = analysis['intensity_db']

            # Emergency bypass
            if analysis['is_emergency']:
                self.emergency_bypass = True
                print(f"\n🚨 EMERGENCY DETECTED: {analysis['noise_class']} "
                      f"(confidence: {analysis['confidence']:.2%})")
                print("   ANC bypassed for safety!")

        # Generate anti-noise if ANC enabled and no emergency
        anti_noise = None
        if self.anc_enabled and not self.emergency_bypass:
            anti_noise = self.anti_noise_gen.generate_anti_noise(
                audio_data,
                amplitude_match=self.noise_intensity_threshold
            )

        return anti_noise, analysis

    def audio_capture_thread(self, duration=None):
        """Capture audio from microphone in background thread."""

        print("\n[CAPTURE] Starting audio capture thread...")

        try:
            # Open input stream
            input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            print("[CAPTURE] Input stream opened")

            start_time = time.time()

            while self.running:
                # Check duration limit
                if duration and (time.time() - start_time) > duration:
                    break

                # Read audio chunk
                try:
                    audio_bytes = input_stream.read(self.chunk_size,
                                                    exception_on_overflow=False)
                    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_data = audio_data.astype(np.float32) / 32768.0

                    # Add to queue
                    if not self.audio_queue.full():
                        self.audio_queue.put(audio_data)
                    else:
                        # Drop oldest if queue full
                        try:
                            self.audio_queue.get_nowait()
                            self.audio_queue.put(audio_data)
                        except:
                            pass

                except Exception as e:
                    print(f"[CAPTURE] Read error: {e}")
                    continue

            input_stream.stop_stream()
            input_stream.close()
            print("[CAPTURE] Audio capture thread stopped")

        except Exception as e:
            print(f"[CAPTURE] Error: {e}")
            self.running = False

    def audio_processing_thread(self):
        """Process audio and generate anti-noise in background thread."""

        print("\n[PROCESS] Starting audio processing thread...")

        try:
            # Open output stream
            output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )

            print("[PROCESS] Output stream opened")

            while self.running:
                try:
                    # Get audio from queue
                    audio_data = self.audio_queue.get(timeout=1.0)

                    # Process audio
                    anti_noise, analysis = self.process_audio_chunk(audio_data)

                    # Output anti-noise if available
                    if anti_noise is not None:
                        # Convert to int16 for playback
                        anti_noise_int16 = (anti_noise * 32768).astype(np.int16)
                        output_stream.write(anti_noise_int16.tobytes())
                    else:
                        # Output silence if ANC disabled or emergency
                        silence = np.zeros(self.chunk_size, dtype=np.int16)
                        output_stream.write(silence.tobytes())

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[PROCESS] Processing error: {e}")
                    continue

            output_stream.stop_stream()
            output_stream.close()
            print("[PROCESS] Audio processing thread stopped")

        except Exception as e:
            print(f"[PROCESS] Error: {e}")
            self.running = False

    def status_display_thread(self):
        """Display status updates in console."""

        print("\n[STATUS] Starting status display thread...")

        last_class = None
        last_emergency = False

        while self.running:
            time.sleep(2.0)

            with self.state_lock:
                # Display on change
                if (self.current_noise_class != last_class or
                    self.emergency_detected != last_emergency):

                    print(f"\n[STATUS] {datetime.now().strftime('%H:%M:%S')}")
                    print(f"  ANC: {'ENABLED' if self.anc_enabled else 'DISABLED'}")
                    print(f"  Noise: {self.current_noise_class} "
                          f"(confidence: {self.current_confidence:.1%})")
                    print(f"  Intensity: {self.current_intensity:.1f} dB")
                    print(f"  Emergency: {'YES - BYPASS ACTIVE' if self.emergency_bypass else 'No'}")
                    print(f"  Stats: {self.stats['total_detections']} detections, "
                          f"{self.stats['emergency_count']} emergencies")

                    last_class = self.current_noise_class
                    last_emergency = self.emergency_detected

        print("[STATUS] Status display thread stopped")

    def start_realtime_anc(self, duration=None):
        """Start real-time ANC system."""

        print("\n" + "="*80)
        print("STARTING REAL-TIME ANC SYSTEM")
        print("="*80)

        self.running = True
        self.anc_enabled = True
        self.stats['start_time'] = time.time()

        # Start threads
        threads = []

        # Capture thread
        capture_thread = threading.Thread(
            target=self.audio_capture_thread,
            args=(duration,),
            daemon=True
        )
        capture_thread.start()
        threads.append(capture_thread)

        # Processing thread
        process_thread = threading.Thread(
            target=self.audio_processing_thread,
            daemon=True
        )
        process_thread.start()
        threads.append(process_thread)

        # Status thread
        status_thread = threading.Thread(
            target=self.status_display_thread,
            daemon=True
        )
        status_thread.start()
        threads.append(status_thread)

        print("\n✓ All threads started")
        print("\nPress Ctrl+C to stop...\n")

        try:
            # Wait for threads
            if duration:
                time.sleep(duration + 1)
                self.running = False
            else:
                while self.running:
                    time.sleep(0.1)

            # Wait for threads to finish
            for thread in threads:
                thread.join(timeout=2.0)

        except KeyboardInterrupt:
            print("\n\nStopping ANC system...")
            self.running = False

            for thread in threads:
                thread.join(timeout=2.0)

        # Calculate stats
        if self.stats['start_time']:
            self.stats['anc_active_time'] = int(time.time() - self.stats['start_time'])

        print("\n" + "="*80)
        print("ANC SYSTEM STOPPED")
        print("="*80)
        print(f"\nSession Statistics:")
        print(f"  Total detections: {self.stats['total_detections']}")
        print(f"  Emergency alerts: {self.stats['emergency_count']}")
        print(f"  Active time: {self.stats['anc_active_time']} seconds")
        print("="*80)

    def get_state(self):
        """Get current system state (for web UI integration)."""
        with self.state_lock:
            return {
                'anc_enabled': self.anc_enabled,
                'noise_intensity': self.noise_intensity_threshold,
                'current_noise_class': self.current_noise_class,
                'emergency_detected': self.emergency_detected,
                'detection_confidence': self.current_confidence,
                'stats': self.stats.copy()
            }

    def set_anc_enabled(self, enabled):
        """Enable/disable ANC."""
        with self.state_lock:
            self.anc_enabled = enabled
            if not enabled:
                self.emergency_bypass = False

    def set_noise_intensity(self, intensity):
        """Set noise intensity threshold (0.0 - 1.0)."""
        with self.state_lock:
            self.noise_intensity_threshold = max(0.0, min(1.0, intensity))

    def reset_emergency(self):
        """Reset emergency bypass."""
        with self.state_lock:
            self.emergency_bypass = False
            self.emergency_detected = False

    def cleanup(self):
        """Cleanup resources."""
        print("\nCleaning up...")
        self.running = False

        if hasattr(self, 'audio') and self.audio is not None:
            self.audio.terminate()

        if hasattr(self, 'db'):
            self.db.close()

        print("✓ Cleanup complete")


class ANCSystemWithWebUI:
    """ANC System with integrated Flask web UI."""

    def __init__(self, anc_core):
        """Initialize with ANC core system."""
        self.anc_core = anc_core

        # Import Flask app
        try:
            from app import app, state, state_lock
            self.flask_app = app
            self.web_state = state
            self.web_lock = state_lock
            print("\n✓ Flask web UI loaded")
        except ImportError as e:
            print(f"\n⚠ Flask web UI not available: {e}")
            self.flask_app = None

    def sync_state_to_web(self):
        """Sync ANC core state to web UI state."""
        if not self.flask_app:
            return

        core_state = self.anc_core.get_state()

        with self.web_lock:
            self.web_state.anc_enabled = core_state['anc_enabled']
            self.web_state.noise_intensity = core_state['noise_intensity']
            self.web_state.current_noise_class = core_state['current_noise_class']
            self.web_state.emergency_detected = core_state['emergency_detected']
            self.web_state.detection_confidence = core_state['detection_confidence']
            self.web_state.stats = core_state['stats']

    def sync_state_from_web(self):
        """Sync web UI state to ANC core state."""
        if not self.flask_app:
            return

        with self.web_lock:
            self.anc_core.set_anc_enabled(self.web_state.anc_enabled)
            self.anc_core.set_noise_intensity(self.web_state.noise_intensity)

    def state_sync_thread(self):
        """Background thread to sync states."""
        while self.anc_core.running:
            # Sync core -> web
            self.sync_state_to_web()

            # Sync web -> core
            self.sync_state_from_web()

            time.sleep(0.5)

    def start_with_web_ui(self, host='0.0.0.0', port=5000, anc_duration=None):
        """Start ANC system with web UI."""

        if not self.flask_app:
            print("Flask web UI not available, starting core only...")
            self.anc_core.start_realtime_anc(duration=anc_duration)
            return

        print("\n" + "="*80)
        print("STARTING ANC SYSTEM WITH WEB UI")
        print("="*80)

        # Start ANC in background
        anc_thread = threading.Thread(
            target=self.anc_core.start_realtime_anc,
            args=(anc_duration,),
            daemon=True
        )
        anc_thread.start()

        # Start state sync thread
        sync_thread = threading.Thread(
            target=self.state_sync_thread,
            daemon=True
        )
        sync_thread.start()

        # Give ANC time to start
        time.sleep(2)

        print(f"\n✓ Starting web UI on http://{host}:{port}")
        print(f"  Access from mobile: http://<your-ip>:{port}")
        print("\nPress Ctrl+C to stop both ANC and web UI\n")

        try:
            # Start Flask (blocking)
            self.flask_app.run(host=host, port=port, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n\nStopping system...")
            self.anc_core.running = False
            anc_thread.join(timeout=5.0)


def main():
    """Main entry point with CLI interface."""

    parser = argparse.ArgumentParser(
        description="Active Noise Cancellation System - Full Integration"
    )

    parser.add_argument(
        '--mode',
        choices=['core', 'web'],
        default='core',
        help="Run mode: 'core' (ANC only) or 'web' (ANC + Web UI)"
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help="Duration in seconds (default: run until Ctrl+C)"
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help="Web UI host (default: 0.0.0.0)"
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help="Web UI port (default: 5000)"
    )

    parser.add_argument(
        '--db',
        default='anc_system.db',
        help="Database path (default: anc_system.db)"
    )

    args = parser.parse_args()

    # Initialize ANC core
    anc_core = ANCSystemCore(db_path=args.db)

    try:
        if args.mode == 'core':
            # Run ANC core only
            anc_core.start_realtime_anc(duration=args.duration)

        elif args.mode == 'web':
            # Run ANC with web UI
            anc_with_web = ANCSystemWithWebUI(anc_core)
            anc_with_web.start_with_web_ui(
                host=args.host,
                port=args.port,
                anc_duration=args.duration
            )

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        anc_core.cleanup()


if __name__ == "__main__":
    main()
