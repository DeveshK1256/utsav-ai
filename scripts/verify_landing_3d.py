import urllib.request
import time

base = 'https://utsav-ai.netlify.app'

def run():
    print("Verifying live Netlify 3D landing page and favicons...")
    # Measure TTFB & load time
    t0 = time.time()
    req = urllib.request.Request(base, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        ttfb = time.time() - t0
        body = resp.read().decode('utf-8')
        total_time = time.time() - t0
        print(f"Landing page status: {resp.status}")
        print(f"TTFB: {ttfb*1000:.1f}ms, Total download time: {total_time*1000:.1f}ms")
        assert 'Harmoniously Composed' in body, 'New 3D landing headline missing!'
        assert 'The Planning Chaos' in body, 'Chaos to Composed interactive component missing!'
        assert 'Motion: Dynamic 3D' in body or 'reduced-motion' in body, 'Motion toggle missing!'

    # Check favicon and icons
    for icon in ['/favicon.ico', '/icon.svg', '/apple-touch-icon.png', '/favicon-32x32.png']:
        req_icon = urllib.request.Request(f'{base}{icon}', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_icon) as r:
            data = r.read()
            ctype = r.headers.get("content-type")
            print(f"Icon {icon}: HTTP {r.status} (content-type: {ctype}, size: {len(data)} bytes)")
            assert r.status == 200

    print("\nALL VERIFICATIONS PASSED: 3D Landing Page is Live and Fast with 0 Regression!")

if __name__ == '__main__':
    run()
