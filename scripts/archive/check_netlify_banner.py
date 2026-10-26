import httpx
import re

r = httpx.get("https://utsav-ai.netlify.app/dashboard/events/default")
scripts = re.findall(r'src="([^"]+\.js)"', r.text)
print(f"Found {len(scripts)} scripts on Netlify /dashboard/events/default")
found = False
for s in scripts:
    url = f"https://utsav-ai.netlify.app{s}" if s.startswith("/") else s
    try:
        res = httpx.get(url, timeout=10.0)
        if "Mandatory Priest & Elder Review Required" in res.text or "AI-Drafted Baseline" in res.text:
            print("SUCCESS: Found review required banner in Netlify bundle chunk:", s)
            found = True
            break
    except Exception as e:
        pass

if not found:
    print("Netlify build is compiling. Let's wait a moment.")
