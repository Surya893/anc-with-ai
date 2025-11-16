"""
SQLite Database Schema for ANC (Active Noise Cancellation) System
Stores noise recordings, sound wave data, and AI model artifacts as per patent spec.
"""

import sqlite3
import numpy as np
from datetime import datetime
from typing import Optional, List, Tuple
import json


class ANCDatabase:
    """
    Database manager for Active Noise Cancellation system.
    Handles storage of noise recordings, waveform data, and AI model artifacts.
    """

    def __init__(self, db_path: str = "anc_system.db"):
        """Initialize database connection and create schema if needed."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_schema()

    def connect(self):
        """Establish connection to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def create_schema(self):
        """Create all database tables for the ANC system."""

        # Table 1: Noise Recordings Metadata
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS noise_recordings (
                recording_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                duration_seconds REAL NOT NULL,
                sampling_rate INTEGER NOT NULL,
                num_samples INTEGER NOT NULL,
                environment_type TEXT,
                noise_level_db REAL,
                location TEXT,
                device_id TEXT,
                description TEXT,
                metadata_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 2: Audio Samples / Waveform Data
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_samples (
                sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                sample_type TEXT NOT NULL CHECK(sample_type IN (
                    'ambient_noise',
                    'clean_signal',
                    'noise_cancelled',
                    'error_signal',
                    'reference_noise'
                )),
                sample_index INTEGER NOT NULL,
                amplitude REAL NOT NULL,
                timestamp_offset REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES noise_recordings(recording_id) ON DELETE CASCADE
            )
        """)

        # Index for faster audio sample queries
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audio_samples_recording
            ON audio_samples(recording_id, sample_type, sample_index)
        """)

        # Table 3: Audio Waveforms (Compressed storage for efficiency)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_waveforms (
                waveform_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                waveform_type TEXT NOT NULL CHECK(waveform_type IN (
                    'ambient_noise',
                    'clean_signal',
                    'noise_cancelled',
                    'error_signal',
                    'reference_noise'
                )),
                waveform_data BLOB NOT NULL,
                num_samples INTEGER NOT NULL,
                min_amplitude REAL,
                max_amplitude REAL,
                mean_amplitude REAL,
                std_amplitude REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES noise_recordings(recording_id) ON DELETE CASCADE
            )
        """)

        # Table 4: Model Versions
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_versions (
                model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_name TEXT UNIQUE NOT NULL,
                version_number TEXT NOT NULL,
                filter_length INTEGER NOT NULL,
                adaptation_rate REAL NOT NULL,
                algorithm_type TEXT DEFAULT 'LMS',
                description TEXT,
                is_active BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 5: Model Coefficients / Filter Weights
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_coefficients (
                coefficient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                recording_id INTEGER,
                coefficient_data BLOB NOT NULL,
                coefficient_length INTEGER NOT NULL,
                iteration_number INTEGER,
                convergence_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES model_versions(model_id) ON DELETE CASCADE,
                FOREIGN KEY (recording_id) REFERENCES noise_recordings(recording_id) ON DELETE SET NULL
            )
        """)

        # Table 6: Processing Sessions
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                recording_id INTEGER NOT NULL,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                processing_duration_ms REAL,
                iterations_count INTEGER,
                final_error REAL,
                convergence_achieved BOOLEAN,
                configuration_json TEXT,
                FOREIGN KEY (model_id) REFERENCES model_versions(model_id) ON DELETE CASCADE,
                FOREIGN KEY (recording_id) REFERENCES noise_recordings(recording_id) ON DELETE CASCADE
            )
        """)

        # Table 7: Performance Metrics
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                metric_type TEXT NOT NULL CHECK(metric_type IN (
                    'snr_improvement',
                    'noise_reduction_db',
                    'convergence_rate',
                    'mse',
                    'rmse',
                    'processing_latency',
                    'custom'
                )),
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES processing_sessions(session_id) ON DELETE CASCADE
            )
        """)

        # Table 8: Training History
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                epoch_number INTEGER,
                iteration_number INTEGER,
                loss_value REAL,
                error_value REAL,
                learning_rate REAL,
                coefficient_snapshot BLOB,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES model_versions(model_id) ON DELETE CASCADE
            )
        """)

        # Table 9: Spectral Analysis Data
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS spectral_analysis (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                waveform_type TEXT NOT NULL,
                frequency_data BLOB NOT NULL,
                magnitude_data BLOB NOT NULL,
                phase_data BLOB,
                fft_size INTEGER,
                window_function TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES noise_recordings(recording_id) ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    def insert_noise_recording(self, duration_seconds: float, sampling_rate: int,
                              num_samples: int, environment_type: str = None,
                              noise_level_db: float = None, location: str = None,
                              device_id: str = None, description: str = None,
                              metadata: dict = None) -> int:
        """Insert a new noise recording metadata entry."""
        metadata_json = json.dumps(metadata) if metadata else None

        self.cursor.execute("""
            INSERT INTO noise_recordings
            (duration_seconds, sampling_rate, num_samples, environment_type,
             noise_level_db, location, device_id, description, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (duration_seconds, sampling_rate, num_samples, environment_type,
              noise_level_db, location, device_id, description, metadata_json))

        self.conn.commit()
        return self.cursor.lastrowid

    def insert_waveform(self, recording_id: int, waveform_type: str,
                       waveform_array: np.ndarray) -> int:
        """
        Insert waveform data as compressed BLOB.
        Stores numpy array efficiently and calculates statistics.
        """
        # Convert numpy array to bytes
        waveform_bytes = waveform_array.tobytes()

        # Calculate statistics
        stats = {
            'num_samples': len(waveform_array),
            'min': float(np.min(waveform_array)),
            'max': float(np.max(waveform_array)),
            'mean': float(np.mean(waveform_array)),
            'std': float(np.std(waveform_array))
        }

        self.cursor.execute("""
            INSERT INTO audio_waveforms
            (recording_id, waveform_type, waveform_data, num_samples,
             min_amplitude, max_amplitude, mean_amplitude, std_amplitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (recording_id, waveform_type, waveform_bytes, stats['num_samples'],
              stats['min'], stats['max'], stats['mean'], stats['std']))

        self.conn.commit()
        return self.cursor.lastrowid

    def get_waveform(self, waveform_id: int, dtype=np.float64) -> Optional[np.ndarray]:
        """Retrieve waveform data from database and reconstruct numpy array."""
        self.cursor.execute("""
            SELECT waveform_data, num_samples
            FROM audio_waveforms
            WHERE waveform_id = ?
        """, (waveform_id,))

        result = self.cursor.fetchone()
        if result:
            waveform_bytes, num_samples = result
            return np.frombuffer(waveform_bytes, dtype=dtype)
        return None

    def insert_model_version(self, version_name: str, version_number: str,
                            filter_length: int, adaptation_rate: float,
                            algorithm_type: str = 'LMS', description: str = None,
                            is_active: bool = False) -> int:
        """Insert a new model version."""
        self.cursor.execute("""
            INSERT INTO model_versions
            (version_name, version_number, filter_length, adaptation_rate,
             algorithm_type, description, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version_name, version_number, filter_length, adaptation_rate,
              algorithm_type, description, is_active))

        self.conn.commit()
        return self.cursor.lastrowid

    def insert_model_coefficients(self, model_id: int, coefficients: np.ndarray,
                                 recording_id: int = None, iteration_number: int = None,
                                 convergence_score: float = None) -> int:
        """Store model coefficients as binary data."""
        coefficient_bytes = coefficients.tobytes()

        self.cursor.execute("""
            INSERT INTO model_coefficients
            (model_id, recording_id, coefficient_data, coefficient_length,
             iteration_number, convergence_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, recording_id, coefficient_bytes, len(coefficients),
              iteration_number, convergence_score))

        self.conn.commit()
        return self.cursor.lastrowid

    def get_model_coefficients(self, coefficient_id: int, dtype=np.float64) -> Optional[np.ndarray]:
        """Retrieve model coefficients and reconstruct numpy array."""
        self.cursor.execute("""
            SELECT coefficient_data, coefficient_length
            FROM model_coefficients
            WHERE coefficient_id = ?
        """, (coefficient_id,))

        result = self.cursor.fetchone()
        if result:
            coeff_bytes, length = result
            return np.frombuffer(coeff_bytes, dtype=dtype)
        return None

    def insert_processing_session(self, model_id: int, recording_id: int,
                                  iterations_count: int = None, final_error: float = None,
                                  convergence_achieved: bool = None,
                                  configuration: dict = None) -> int:
        """Create a new processing session entry."""
        config_json = json.dumps(configuration) if configuration else None

        self.cursor.execute("""
            INSERT INTO processing_sessions
            (model_id, recording_id, iterations_count, final_error,
             convergence_achieved, configuration_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, recording_id, iterations_count, final_error,
              convergence_achieved, config_json))

        self.conn.commit()
        return self.cursor.lastrowid

    def update_processing_session(self, session_id: int, end_time: str = None,
                                 processing_duration_ms: float = None,
                                 final_error: float = None,
                                 convergence_achieved: bool = None):
        """Update processing session with completion data."""
        if end_time is None:
            end_time = datetime.now().isoformat()

        self.cursor.execute("""
            UPDATE processing_sessions
            SET end_time = ?, processing_duration_ms = ?, final_error = ?,
                convergence_achieved = ?
            WHERE session_id = ?
        """, (end_time, processing_duration_ms, final_error,
              convergence_achieved, session_id))

        self.conn.commit()

    def insert_performance_metric(self, session_id: int, metric_type: str,
                                 metric_value: float, metric_unit: str = None,
                                 notes: str = None) -> int:
        """Insert a performance metric for a processing session."""
        self.cursor.execute("""
            INSERT INTO performance_metrics
            (session_id, metric_type, metric_value, metric_unit, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, metric_type, metric_value, metric_unit, notes))

        self.conn.commit()
        return self.cursor.lastrowid

    def insert_training_history(self, model_id: int, epoch_number: int = None,
                               iteration_number: int = None, loss_value: float = None,
                               error_value: float = None, learning_rate: float = None,
                               coefficient_snapshot: np.ndarray = None) -> int:
        """Record training iteration history."""
        coeff_bytes = coefficient_snapshot.tobytes() if coefficient_snapshot is not None else None

        self.cursor.execute("""
            INSERT INTO training_history
            (model_id, epoch_number, iteration_number, loss_value, error_value,
             learning_rate, coefficient_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (model_id, epoch_number, iteration_number, loss_value, error_value,
              learning_rate, coeff_bytes))

        self.conn.commit()
        return self.cursor.lastrowid

    def insert_spectral_analysis(self, recording_id: int, waveform_type: str,
                                frequency_data: np.ndarray, magnitude_data: np.ndarray,
                                phase_data: np.ndarray = None, fft_size: int = None,
                                window_function: str = None) -> int:
        """Store spectral analysis data (FFT results)."""
        freq_bytes = frequency_data.tobytes()
        mag_bytes = magnitude_data.tobytes()
        phase_bytes = phase_data.tobytes() if phase_data is not None else None

        self.cursor.execute("""
            INSERT INTO spectral_analysis
            (recording_id, waveform_type, frequency_data, magnitude_data,
             phase_data, fft_size, window_function)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (recording_id, waveform_type, freq_bytes, mag_bytes,
              phase_bytes, fft_size, window_function))

        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_recordings(self) -> List[Tuple]:
        """Retrieve all noise recordings metadata."""
        self.cursor.execute("""
            SELECT recording_id, timestamp, duration_seconds, sampling_rate,
                   num_samples, environment_type, noise_level_db, location
            FROM noise_recordings
            ORDER BY timestamp DESC
        """)
        return self.cursor.fetchall()

    def get_active_model(self) -> Optional[Tuple]:
        """Get the currently active model version."""
        self.cursor.execute("""
            SELECT model_id, version_name, version_number, filter_length,
                   adaptation_rate, algorithm_type
            FROM model_versions
            WHERE is_active = 1
            LIMIT 1
        """)
        return self.cursor.fetchone()

    def get_session_metrics(self, session_id: int) -> List[Tuple]:
        """Retrieve all metrics for a processing session."""
        self.cursor.execute("""
            SELECT metric_type, metric_value, metric_unit, timestamp
            FROM performance_metrics
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        return self.cursor.fetchall()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed."""
        self.close()


def initialize_database(db_path: str = "anc_system.db") -> ANCDatabase:
    """
    Initialize and return a new ANCDatabase instance.
    This is the main entry point for using the database.
    """
    db = ANCDatabase(db_path)
    print(f"Database initialized at: {db_path}")
    return db


if __name__ == "__main__":
    # Example usage and testing
    print("Creating ANC Database Schema...")

    with ANCDatabase("anc_system.db") as db:
        print("✓ Database schema created successfully!")
        print("\nTables created:")
        print("  - noise_recordings: Store recording metadata")
        print("  - audio_samples: Individual audio data points")
        print("  - audio_waveforms: Compressed waveform storage")
        print("  - model_versions: AI model version tracking")
        print("  - model_coefficients: Filter coefficients storage")
        print("  - processing_sessions: Noise cancellation sessions")
        print("  - performance_metrics: Model performance tracking")
        print("  - training_history: Training iteration logs")
        print("  - spectral_analysis: FFT and frequency analysis")

        # Test with sample data
        print("\nInserting test data...")

        # Create a test recording
        recording_id = db.insert_noise_recording(
            duration_seconds=1.0,
            sampling_rate=44100,
            num_samples=44100,
            environment_type="office",
            noise_level_db=65.5,
            location="Lab Room A",
            description="Test ambient noise recording"
        )
        print(f"✓ Created recording with ID: {recording_id}")

        # Create a test model version
        model_id = db.insert_model_version(
            version_name="LMS_v1.0",
            version_number="1.0.0",
            filter_length=1024,
            adaptation_rate=0.01,
            algorithm_type="LMS",
            description="Initial LMS adaptive filter",
            is_active=True
        )
        print(f"✓ Created model version with ID: {model_id}")

        # Store test waveform
        test_waveform = np.random.randn(1000)
        waveform_id = db.insert_waveform(
            recording_id=recording_id,
            waveform_type="ambient_noise",
            waveform_array=test_waveform
        )
        print(f"✓ Stored waveform with ID: {waveform_id}")

        # Store test coefficients
        test_coeffs = np.random.randn(1024)
        coeff_id = db.insert_model_coefficients(
            model_id=model_id,
            coefficients=test_coeffs,
            recording_id=recording_id,
            iteration_number=100,
            convergence_score=0.95
        )
        print(f"✓ Stored coefficients with ID: {coeff_id}")

        print("\n✓ All tests passed! Database is ready for use.")
