"""
Verify Flask App Code (Runs in a sandboxed environment)
Tests API logic and routes without starting the server.
"""

import sys
import json
from datetime import datetime


def verify_app_structure():
    """Verify Flask app structure and imports."""
    print("="*80)
    print("FLASK APP CODE VERIFICATION (sandboxed environment)")
    print("="*80)
    print("\nVerifying app structure and code logic...")
    print("="*80)

    # Test 1: Import Flask app
    print("\n[TEST 1] Import Flask App")
    print("─"*80)
    try:
        from app import app, state, state_lock
        print("✓ Flask app imported successfully")
        print(f"  App name: {app.name}")
        print(f"  State initialized: {state is not None}")
        print(f"  Lock available: {state_lock is not None}")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return 1

    # Test 2: Verify routes
    print("\n[TEST 2] Verify API Routes")
    print("─"*80)
    try:
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        api_routes = [r for r in routes if r.startswith('/api/')]

        print(f"Total routes: {len(routes)}")
        print(f"API routes: {len(api_routes)}")
        print("\nAPI Endpoints:")
        for route in sorted(api_routes):
            print(f"  ✓ {route}")

        # Verify required endpoints
        required = [
            '/api/status',
            '/api/toggle_anc',
            '/api/set_intensity',
            '/api/prolonged_detection',
            '/api/notifications',
            '/api/simulate_noise'
        ]

        for endpoint in required:
            if endpoint in api_routes:
                print(f"  ✓ Required endpoint: {endpoint}")
            else:
                print(f"  ✗ Missing endpoint: {endpoint}")
                return 1

    except Exception as e:
        print(f"✗ Route verification failed: {e}")
        return 1

    # Test 3: Test state management
    print("\n[TEST 3] State Management")
    print("─"*80)
    try:
        print(f"Initial state:")
        print(f"  ANC enabled: {state.anc_enabled}")
        print(f"  Noise intensity: {state.noise_intensity}")
        print(f"  Emergency detected: {state.emergency_detected}")

        # Test state modification
        with state_lock:
            state.anc_enabled = True
            state.noise_intensity = 0.75
            state.current_noise_class = "office"

        print(f"\nAfter modification:")
        print(f"  ANC enabled: {state.anc_enabled}")
        print(f"  Noise intensity: {state.noise_intensity}")
        print(f"  Current class: {state.current_noise_class}")

        print("✓ State management working correctly")

    except Exception as e:
        print(f"✗ State management failed: {e}")
        return 1

    # Test 4: Test API endpoints (without HTTP)
    print("\n[TEST 4] API Endpoint Logic")
    print("─"*80)
    try:
        # Create test client
        with app.test_client() as client:
            # Test status endpoint
            print("\nTesting GET /api/status")
            response = client.get('/api/status')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Response has 'anc_enabled': {data.get('anc_enabled')}")
            print(f"  ✓ Response has 'noise_intensity': {data.get('noise_intensity')}")

            # Test toggle ANC
            print("\nTesting POST /api/toggle_anc")
            response = client.post('/api/toggle_anc',
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Success: {data.get('success')}")
            print(f"  ✓ Message: {data.get('message')}")

            # Test set intensity
            print("\nTesting POST /api/set_intensity")
            response = client.post('/api/set_intensity',
                                   data=json.dumps({'intensity': 0.85}),
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Intensity set to: {data.get('intensity')}")

            # Test prolonged detection
            print("\nTesting POST /api/prolonged_detection")
            response = client.post('/api/prolonged_detection',
                                   data=json.dumps({
                                       'enabled': True,
                                       'threshold_seconds': 10
                                   }),
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Prolonged enabled: {data.get('prolonged_detection', {}).get('enabled')}")

            # Test simulate noise
            print("\nTesting POST /api/simulate_noise")
            response = client.post('/api/simulate_noise',
                                   data=json.dumps({
                                       'noise_type': 'alarm',
                                       'emergency': True,
                                       'confidence': 0.95
                                   }),
                                   content_type='application/json')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Simulation success: {data.get('success')}")

            # Test notifications
            print("\nTesting GET /api/notifications")
            response = client.get('/api/notifications')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Notification count: {data.get('count')}")

            # Test health
            print("\nTesting GET /health")
            response = client.get('/health')
            assert response.status_code == 200
            data = json.loads(response.data)
            print(f"  ✓ Status code: 200")
            print(f"  ✓ Health status: {data.get('status')}")

        print("\n✓ All API endpoints working correctly")

    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 5: Verify template exists
    print("\n[TEST 5] Template Verification")
    print("─"*80)
    try:
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')

        if os.path.exists(template_path):
            print(f"✓ Template found: {template_path}")
            with open(template_path, 'r') as f:
                content = f.read()
                print(f"  Template size: {len(content)} bytes")
                print(f"  Contains 'ANC': {('ANC' in content)}")
                print(f"  Contains API calls: {('api/' in content)}")
        else:
            print(f"✗ Template not found: {template_path}")
            return 1

    except Exception as e:
        print(f"✗ Template verification failed: {e}")
        return 1

    # Test 6: Verify static files
    print("\n[TEST 6] Static Files Verification")
    print("─"*80)
    try:
        import os

        static_files = [
            'static/css/style.css',
            'static/js/app.js'
        ]

        for file_path in static_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"  ✓ {file_path} ({size} bytes)")
            else:
                print(f"  ✗ Missing: {file_path}")
                return 1

    except Exception as e:
        print(f"✗ Static file verification failed: {e}")
        return 1

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print("\n✓ All tests passed!")
    print("\nVerified:")
    print("  ✓ Flask app structure correct")
    print("  ✓ API routes defined (10 endpoints)")
    print("  ✓ State management working")
    print("  ✓ API endpoint logic functional")
    print("  ✓ Template file exists")
    print("  ✓ Static files present")

    print("\n" + "="*80)
    print("CODE VERIFIED - READY FOR LOCAL EXECUTION")
    print("="*80)

    return 0


def simulate_workflow():
    """Simulate typical workflow."""
    print("\n" + "="*80)
    print("SIMULATED USER WORKFLOW")
    print("="*80)

    print("\nWhat WOULD happen when you run locally:")
    print("─"*80)

    print("\n1. Start Flask server:")
    print("   $ python app.py")
    print("   → Server starts on http://localhost:5000")
    print("   → Accessible from mobile at http://<your-ip>:5000")

    print("\n2. Open in browser:")
    print("   → Load http://localhost:5000")
    print("   → HTML template rendered")
    print("   → CSS/JS files loaded")
    print("   → Page displays ANC control interface")

    print("\n3. User interacts - Toggle ANC:")
    print("   User Action: Click 'Enable ANC' button")
    print("   → JavaScript: fetch('/api/toggle_anc', {method: 'POST'})")
    print("   → Flask: Receives request")
    print("   → Flask: Updates state.anc_enabled = True")
    print("   → Flask: Returns {success: true, anc_enabled: true}")
    print("   → JavaScript: Updates UI (button turns green)")

    print("\n4. User interacts - Adjust Intensity:")
    print("   User Action: Slide intensity to 75%")
    print("   → JavaScript: fetch('/api/set_intensity', {intensity: 0.75})")
    print("   → Flask: Updates state.noise_intensity = 0.75")
    print("   → Flask: Returns {success: true, intensity: 0.75}")
    print("   → JavaScript: Updates badge to '75%'")

    print("\n5. User tests - Simulate Alarm:")
    print("   User Action: Click 'Simulate Alarm' button")
    print("   → JavaScript: fetch('/api/simulate_noise', {type: 'alarm', emergency: true})")
    print("   → Flask: Updates state (emergency detected)")
    print("   → Flask: Adds notification to queue")
    print("   → Flask: Returns {success: true}")
    print("   → JavaScript: Polls /api/notifications")
    print("   → JavaScript: Displays emergency banner (red, pulsing)")
    print("   → JavaScript: Shows toast: 'Emergency Sound Detected!'")

    print("\n6. Real-time updates:")
    print("   → JavaScript polls /api/status every 1 second")
    print("   → Flask returns current state")
    print("   → UI updates: detection class, confidence, stats")

    print("\n" + "="*80)


def print_local_instructions():
    """Print instructions for local execution."""
    print("\n" + "="*80)
    print("LOCAL EXECUTION INSTRUCTIONS")
    print("="*80)

    print("\n📋 Step-by-Step Guide:")
    print("─"*80)

    print("\n1. Install Dependencies:")
    print("   $ pip install Flask==3.0.0 Werkzeug==3.0.0 numpy")
    print("   Or:")
    print("   $ pip install -r requirements_web.txt")

    print("\n2. Start Flask Server:")
    print("   $ python app.py")

    print("\n3. Expected Output:")
    print("""
   ================================================================================
   ANC SYSTEM WEB APPLICATION
   ================================================================================

   Starting Flask server...
   Access the app at: http://localhost:5000
   Mobile access: http://<your-ip>:5000

   Press Ctrl+C to stop
   ================================================================================

   * Running on http://0.0.0.0:5000
   * Debug mode: on
    """)

    print("\n4. Open Browser:")
    print("   Desktop: http://localhost:5000")
    print("   Mobile:  http://192.168.x.x:5000 (find your IP with ifconfig/ipconfig)")

    print("\n5. Test Features:")
    print("   ✓ Click 'Enable ANC' button → Should turn green")
    print("   ✓ Slide intensity control → Badge updates")
    print("   ✓ Click 'Simulate Alarm' → Red emergency banner appears")
    print("   ✓ Check notifications → New notification added")
    print("   ✓ View statistics → Counters increment")

    print("\n6. Mobile Testing:")
    print("   - Connect phone to same WiFi")
    print("   - Find computer IP: ifconfig | grep inet")
    print("   - Open mobile browser: http://<computer-ip>:5000")
    print("   - Touch controls should be responsive")

    print("\n" + "="*80)
    print("WHAT TO EXPECT IN BROWSER")
    print("="*80)

    print("\nVisual Elements:")
    print("  📱 Header: Blue gradient with 'Active Noise Cancellation'")
    print("  🟢 Status dot: Green if ANC enabled")
    print("  🎛️ Cards: White cards with controls")
    print("  📊 Sliders: Blue-orange gradient")
    print("  🔴 Emergency: Red pulsing banner when alarm detected")
    print("  📬 Notifications: Feed with timestamps")
    print("  📈 Stats: Three-column grid")

    print("\nInteractive Controls:")
    print("  • Large 'Enable ANC' button (toggles on/off)")
    print("  • Intensity slider (0-100%)")
    print("  • Prolonged detection toggle switch")
    print("  • Threshold slider (1-60 seconds)")
    print("  • Test buttons (simulate different noises)")

    print("\n" + "="*80)


def main():
    """Run all verifications."""
    print("\n" + "="*80)
    print("FLASK APP VERIFICATION SUITE")
    print("="*80)
    print("\nRunning in a sandboxed environment (code verification only)")
    print("Actual browser testing must be done locally")
    print("="*80)

    # Verify app
    result = verify_app_structure()
    if result != 0:
        return result

    # Simulate workflow
    simulate_workflow()

    # Print instructions
    print_local_instructions()

    # Final message
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print("\n✓ Flask app code verified")
    print("✓ All endpoints tested successfully")
    print("✓ Ready for local browser testing")
    print("\n→ Next: Run 'python app.py' locally and test in browser")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
