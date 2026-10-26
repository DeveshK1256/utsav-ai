import httpx

r = httpx.get("https://utsav-ai-ycg2.onrender.com/api/v1/discovery/vendors?lat=18.485&lng=73.812&radius_km=15.0")
data = r.json()
print(f"Pune Geo Query (lat=18.485, lng=73.812, Karve Nagar) -> HTTP {r.status_code}, Found {data['total_results']} venues:")
for v in data["results"]:
    print(f"  • {v['business_name']} ({v['category']}) | Locality: {v['locality']} | Dist: {v['distance_km']} km | Rating: {v['rating_tier']} ({v['average_rating']}) | Cost: {v['cost_estimate']['estimated_cost_display']}")
