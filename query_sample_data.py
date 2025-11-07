"""
Query and display sample data from the database
"""
import sqlite3
from datetime import datetime

db_path = "anc_system.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("SAMPLE DATA FROM ANC DATABASE")
print("=" * 80)

# Query recordings
print("\n" + "─" * 80)
print("NOISE RECORDINGS")
print("─" * 80)
cursor.execute("""
    SELECT recording_id, timestamp, duration_seconds, sampling_rate,
           num_samples, environment_type, location, description
    FROM noise_recordings
""")
recordings = cursor.fetchall()
for rec in recordings:
    print(f"\nRecording ID: {rec[0]}")
    print(f"  Timestamp: {rec[1]}")
    print(f"  Duration: {rec[2]}s")
    print(f"  Sampling Rate: {rec[3]} Hz")
    print(f"  Samples: {rec[4]}")
    print(f"  Environment: {rec[5]}")
    print(f"  Location: {rec[6]}")
    print(f"  Description: {rec[7]}")

# Query model versions
print("\n" + "─" * 80)
print("MODEL VERSIONS")
print("─" * 80)
cursor.execute("""
    SELECT model_id, version_name, version_number, filter_length,
           adaptation_rate, algorithm_type, is_active
    FROM model_versions
""")
models = cursor.fetchall()
for model in models:
    active = "✓ ACTIVE" if model[6] else ""
    print(f"\nModel ID: {model[0]} {active}")
    print(f"  Name: {model[1]}")
    print(f"  Version: {model[2]}")
    print(f"  Filter Length: {model[3]}")
    print(f"  Adaptation Rate: {model[4]}")
    print(f"  Algorithm: {model[5]}")

# Query waveforms
print("\n" + "─" * 80)
print("AUDIO WAVEFORMS")
print("─" * 80)
cursor.execute("""
    SELECT waveform_id, recording_id, waveform_type, num_samples,
           min_amplitude, max_amplitude, mean_amplitude, std_amplitude
    FROM audio_waveforms
""")
waveforms = cursor.fetchall()
for wf in waveforms:
    print(f"\nWaveform ID: {wf[0]} (Recording: {wf[1]})")
    print(f"  Type: {wf[2]}")
    print(f"  Samples: {wf[3]}")
    print(f"  Min/Max: {wf[4]:.6f} / {wf[5]:.6f}")
    print(f"  Mean: {wf[6]:.6f}, Std: {wf[7]:.6f}")

# Query processing sessions
print("\n" + "─" * 80)
print("PROCESSING SESSIONS")
print("─" * 80)
cursor.execute("""
    SELECT s.session_id, s.model_id, s.recording_id, s.iterations_count,
           s.final_error, s.convergence_achieved, s.processing_duration_ms,
           m.version_name
    FROM processing_sessions s
    JOIN model_versions m ON s.model_id = m.model_id
""")
sessions = cursor.fetchall()
for sess in sessions:
    conv = "✓ Converged" if sess[5] else "✗ Not converged"
    print(f"\nSession ID: {sess[0]}")
    print(f"  Model: {sess[7]} (ID: {sess[1]})")
    print(f"  Recording ID: {sess[2]}")
    print(f"  Iterations: {sess[3]}")
    print(f"  Final Error: {sess[4]:.6f}")
    print(f"  Status: {conv}")
    print(f"  Duration: {sess[6]:.2f} ms")

# Query performance metrics
print("\n" + "─" * 80)
print("PERFORMANCE METRICS")
print("─" * 80)
cursor.execute("""
    SELECT session_id, metric_type, metric_value, metric_unit
    FROM performance_metrics
    ORDER BY session_id, metric_type
""")
metrics = cursor.fetchall()
for metric in metrics:
    print(f"  Session {metric[0]}: {metric[1]} = {metric[2]:.4f} {metric[3] or ''}")

# Query training history
print("\n" + "─" * 80)
print("TRAINING HISTORY")
print("─" * 80)
cursor.execute("""
    SELECT model_id, iteration_number, error_value, learning_rate
    FROM training_history
    ORDER BY model_id, iteration_number
""")
history = cursor.fetchall()
for hist in history:
    print(f"  Model {hist[0]}, Iteration {hist[1]}: Error = {hist[2]:.6f}, LR = {hist[3]}")

# Query coefficients
print("\n" + "─" * 80)
print("MODEL COEFFICIENTS")
print("─" * 80)
cursor.execute("""
    SELECT coefficient_id, model_id, recording_id, coefficient_length,
           iteration_number, convergence_score
    FROM model_coefficients
""")
coeffs = cursor.fetchall()
for coeff in coeffs:
    print(f"\nCoefficient ID: {coeff[0]}")
    print(f"  Model ID: {coeff[1]}")
    print(f"  Recording ID: {coeff[2]}")
    print(f"  Length: {coeff[3]}")
    print(f"  Iteration: {coeff[4]}")
    print(f"  Convergence Score: {coeff[5]}")

print("\n" + "=" * 80)

conn.close()
