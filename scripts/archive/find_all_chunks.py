import httpx
import re

# Fetch the build manifest
r = httpx.get("https://utsav-ai.netlify.app/_next/static/development/_buildManifest.js")
if r.status_code != 200:
    r = httpx.get("https://utsav-ai.netlify.app/dashboard/events/default")

chunks = re.findall(r'static/chunks/([^\s"\',]+\.js)', r.text)
print(f"Total chunks found in HTML: {len(chunks)}")
for c in chunks:
    chunk_url = f"https://utsav-ai.netlify.app/_next/static/chunks/{c}"
    try:
        res = httpx.get(chunk_url)
        if "Mandatory Priest & Elder Review" in res.text or "AI-Drafted Baseline" in res.text:
            print("SUCCESS! Found banner in chunk:", c)
            break
    except Exception as e:
        pass
else:
    print("Chunk with new banner not detected yet.")
