import httpx

r = httpx.get("https://utsav-ai-ycg2.onrender.com/api/v1/rituals/traditions")
data = r.json()

print(f"TOTAL ROWS RETURNED: {len(data)}")
print("-" * 110)
print(f"{'#':<3} | {'Code':<25} | {'Regional Name':<32} | {'Verified':<8} | {'Source'}")
print("-" * 110)

for idx, t in enumerate(data, 1):
    code = t.get("code") or ""
    name = (t.get("regional_name") or "None")[:30]
    ver = str(t.get("is_verified"))
    src = t.get("verification_source") or "None"
    print(f"{idx:<3} | {code:<25} | {name:<32} | {ver:<8} | {src}")

print("-" * 110)
verified_count = sum(1 for t in data if t.get("is_verified") is True)
print(f"VERIFIED COUNT (is_verified == True): {verified_count}")
print(f"UNVERIFIED COUNT (is_verified == False): {sum(1 for t in data if t.get('is_verified') is False)}")
