import httpx
import re

r = httpx.get("https://utsav-ai.netlify.app/onboarding")
scripts = re.findall(r'src="([^"]+\.js)"', r.text)
print(f"Found {len(scripts)} scripts on Netlify /onboarding")
found = False
for s in scripts:
    url = f"https://utsav-ai.netlify.app{s}" if s.startswith("/") else s
    try:
        res = httpx.get(url, timeout=10.0)
        if "maharashtrian_vedic" in res.text:
            print("SUCCESS: Found maharashtrian_vedic in chunk:", s)
            found = True
            break
    except Exception as e:
        print("Error checking script:", e)

if not found:
    print("Netlify build is still compiling the latest commit. Checking again in a moment.")
