"""
Query the database using SQL to verify the latest recording.
"""

import sqlite3
import json

db_path = "anc_system.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("DATABASE QUERY - LATEST RECORDING")
print("=" * 80)

# Query 1: Get the latest recording metadata
print("\n1. RECORDING METADATA (noise_recordings table)")
print("─" * 80)

cursor.execute("""
    SELECT
        recording_id,
        timestamp,
        duration_seconds,
        sampling_rate,
        num_samples,
        environment_type,
        noise_level_db,
        location,
        device_id,
        description,
        metadata_json
    FROM noise_recordings
    ORDER BY recording_id DESC
    LIMIT 1
""")

rec = cursor.fetchone()
if rec:
    print(f"SQL Query: SELECT * FROM noise_recordings WHERE recording_id = {rec[0]}")
    print(f"\nResults:")
    print(f"  recording_id:      {rec[0]}")
    print(f"  timestamp:         {rec[1]}")
    print(f"  duration_seconds:  {rec[2]}")
    print(f"  sampling_rate:     {rec[3]} Hz")
    print(f"  num_samples:       {rec[4]:,}")
    print(f"  environment_type:  {rec[5]}")
    print(f"  noise_level_db:    {rec[6]:.2f} dB")
    print(f"  location:          {rec[7]}")
    print(f"  device_id:         {rec[8]}")
    print(f"  description:       {rec[9]}")

    if rec[10]:
        metadata = json.loads(rec[10])
        print(f"  metadata_json:")
        for key, value in metadata.items():
            print(f"    - {key}: {value}")

    recording_id = rec[0]

# Query 2: Get waveform data for this recording
print(f"\n2. WAVEFORM DATA (audio_waveforms table)")
print("─" * 80)

cursor.execute("""
    SELECT
        waveform_id,
        waveform_type,
        num_samples,
        min_amplitude,
        max_amplitude,
        mean_amplitude,
        std_amplitude,
        LENGTH(waveform_data) as blob_size
    FROM audio_waveforms
    WHERE recording_id = ?
""", (recording_id,))

waveforms = cursor.fetchall()
print(f"SQL Query: SELECT * FROM audio_waveforms WHERE recording_id = {recording_id}")
print(f"\nResults: {len(waveforms)} waveform(s)")

for wf in waveforms:
    print(f"\n  Waveform ID: {wf[0]}")
    print(f"    waveform_type:   {wf[1]}")
    print(f"    num_samples:     {wf[2]:,}")
    print(f"    min_amplitude:   {wf[3]:.6f}")
    print(f"    max_amplitude:   {wf[4]:.6f}")
    print(f"    mean_amplitude:  {wf[5]:.6f}")
    print(f"    std_amplitude:   {wf[6]:.6f}")
    print(f"    blob_size:       {wf[7]:,} bytes ({wf[7]/1024:.2f} KB)")

# Query 3: Get spectral analysis
print(f"\n3. SPECTRAL ANALYSIS (spectral_analysis table)")
print("─" * 80)

cursor.execute("""
    SELECT
        analysis_id,
        waveform_type,
        fft_size,
        window_function,
        LENGTH(frequency_data) as freq_size,
        LENGTH(magnitude_data) as mag_size,
        LENGTH(phase_data) as phase_size
    FROM spectral_analysis
    WHERE recording_id = ?
""", (recording_id,))

analyses = cursor.fetchall()
print(f"SQL Query: SELECT * FROM spectral_analysis WHERE recording_id = {recording_id}")
print(f"\nResults: {len(analyses)} spectral analysis record(s)")

for analysis in analyses:
    print(f"\n  Analysis ID: {analysis[0]}")
    print(f"    waveform_type:    {analysis[1]}")
    print(f"    fft_size:         {analysis[2]}")
    print(f"    window_function:  {analysis[3]}")
    print(f"    frequency_data:   {analysis[4]:,} bytes")
    print(f"    magnitude_data:   {analysis[5]:,} bytes")
    print(f"    phase_data:       {analysis[6]:,} bytes")

# Query 4: Count total recordings by environment
print(f"\n4. SUMMARY - RECORDINGS BY ENVIRONMENT")
print("─" * 80)

cursor.execute("""
    SELECT
        environment_type,
        COUNT(*) as count,
        AVG(noise_level_db) as avg_noise,
        AVG(duration_seconds) as avg_duration
    FROM noise_recordings
    GROUP BY environment_type
    ORDER BY count DESC
""")

print("SQL Query: SELECT environment_type, COUNT(*), AVG(noise_level_db)")
print("           FROM noise_recordings GROUP BY environment_type\n")

env_stats = cursor.fetchall()
for env in env_stats:
    avg_noise = env[2] if env[2] is not None else 0.0
    avg_duration = env[3] if env[3] is not None else 0.0
    print(f"  {env[0]:<20} Count: {env[1]:>3}  |  Avg Noise: {avg_noise:>7.2f} dB  |  Avg Duration: {avg_duration:.2f}s")

# Query 5: Recent recordings
print(f"\n5. RECENT RECORDINGS (Last 5)")
print("─" * 80)

cursor.execute("""
    SELECT
        recording_id,
        timestamp,
        environment_type,
        location,
        noise_level_db,
        duration_seconds
    FROM noise_recordings
    ORDER BY recording_id DESC
    LIMIT 5
""")

recent = cursor.fetchall()
print("SQL Query: SELECT recording_id, timestamp, environment_type, location")
print("           FROM noise_recordings ORDER BY recording_id DESC LIMIT 5\n")
print(f"{'ID':<6} {'Timestamp':<20} {'Environment':<15} {'Location':<25} {'dB':<8} {'Duration':<10}")
print("─" * 100)

for rec in recent:
    print(f"{rec[0]:<6} {rec[1]:<20} {rec[2]:<15} {rec[3]:<25} {rec[4]:>6.2f}  {rec[5]:>6.2f}s")

# Query 6: Database statistics
print(f"\n6. DATABASE STATISTICS")
print("─" * 80)

cursor.execute("SELECT COUNT(*) FROM noise_recordings")
total_recordings = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM audio_waveforms")
total_waveforms = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM spectral_analysis")
total_analyses = cursor.fetchone()[0]

cursor.execute("SELECT SUM(duration_seconds) FROM noise_recordings")
total_duration = cursor.fetchone()[0]

print(f"  Total Recordings:      {total_recordings}")
print(f"  Total Waveforms:       {total_waveforms}")
print(f"  Total Spectral Analyses: {total_analyses}")
print(f"  Total Recording Time:  {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")

# Get database file size
import os
db_size = os.path.getsize(db_path)
print(f"  Database Size:         {db_size:,} bytes ({db_size/1024:.2f} KB)")

print("\n" + "=" * 80)

conn.close()
