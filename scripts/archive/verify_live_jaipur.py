import httpx

# Query centered near Sanganer, Jaipur (26.817, 75.800) with a 35km radius
url = "https://utsav-ai-ycg2.onrender.com/api/v1/discovery/vendors?lat=26.817&lng=75.800&radius_km=35.0"
print(f"Executing Live Jaipur Query: {url}\n")

r = httpx.get(url, timeout=25.0)
print(f"Status Code: HTTP {r.status_code}")
data = r.json()

print(f"Total Results: {data['total_results']}\n")
print(f"{'#':<3} | {'Venue Name':<45} | {'Locality':<25} | {'Dist (km)':<10} | {'Rating Tier':<14} | {'Cost Estimate':<15}")
print("-" * 125)

for idx, v in enumerate(data["results"], 1):
    cost_disp = v["cost_estimate"]["estimated_cost_display"]
    print(f"{idx:<3} | {v['business_name']:<45} | {v.get('locality') or '-':<25} | {v['distance_km']:<10} | {v['rating_tier']:<14} | {cost_disp:<15}")

# Verify distance sorting
distances = [v["distance_km"] for v in data["results"]]
assert distances == sorted(distances), "Error: Results are not sorted ascending by distance!"

# Verify all are unrated with limited data
for v in data["results"]:
    assert v["rating_tier"] == "new_unrated"
    assert v["average_rating"] is None
    assert v["cost_estimate"]["is_estimate"] is True
    assert v["cost_estimate"]["limited_data"] is True
    assert v["is_verified_profile"] is False
    assert v["coordinate_precision"] == "locality_approximate"

print("\nAll Jaipur assertions verified: Distance sorting is ascending, all venues unrated, all costs limited data, coordinate precision accurately tagged.")
