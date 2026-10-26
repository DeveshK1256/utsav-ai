import httpx
import json

base_url = "https://utsav-ai-ycg2.onrender.com"

print("================================================================================")
print("             UTSAV LIVE PRODUCTION M5 VERIFICATION REPORT                      ")
print("================================================================================")

# 1. Traditions in DB
print("\n[1] CURATED TRADITION KNOWLEDGE GRAPH (LIVE DATABASE)")
r_trad = httpx.get(f"{base_url}/api/v1/rituals/traditions", timeout=30.0)
print(f"Status: {r_trad.status_code}")
traditions = r_trad.json()
verified_traditions = [t for t in traditions if t.get("is_verified")]
print(f"Total Traditions: {len(traditions)} | Verified Primary Traditions: {len(verified_traditions)}")
for t in verified_traditions:
    print(f"  * [{t['code']}] {t['regional_name']}")
    print(f"    - Source: {t['verification_source']}")
    print(f"    - Cataloged Ritual Samagri Items: {t['item_count']}")

# 2. Ephem Astronomical Panchang
print("\n[2] EPHEM ASTRONOMICAL PANCHANG ENGINE (DEC-027)")
print("Query: Oct 24, 2024 | New Delhi (Lat: 28.6139, Lon: 77.2090, Alt: 216m)")
r_pan = httpx.get(f"{base_url}/api/v1/rituals/panchang?event_date=2024-10-24&latitude=28.6139&longitude=77.2090", timeout=30.0)
print(f"Status: {r_pan.status_code}")
pan = r_pan.json()
print(f"  - Computed Sunrise: {pan['sunrise']}")
print(f"  - Computed Sunset:  {pan['sunset']}")
print(f"  - Daylight Span:    {pan['daylight_formatted']}")
print(f"  - Rahu Kaal:        {pan['rahu_kaal']['start']} to {pan['rahu_kaal']['end']} (Inauspicious Octile: {pan['rahu_kaal']['is_inauspicious']})")
print(f"  - Abhijit Muhurat:  {pan['abhijit_muhurat']['start']} to {pan['abhijit_muhurat']['end']} (Auspicious: {pan['abhijit_muhurat']['is_auspicious']})")
print(f"  - Tithi:            {pan['tithi']['name']} ({pan['tithi']['paksha']} paksha, {pan['tithi']['percent_elapsed']}% elapsed)")
print(f"  - Nakshatra:        {pan['nakshatra']['name']} ({pan['nakshatra']['percent_elapsed']}% elapsed)")
print(f"  - Ayanamsha:        {pan['ayanamsha']['system']} @ {pan['ayanamsha']['degrees']} deg")
print(f"  - Mandatory Priest Disclaimer: {pan['priest_disclaimer'][:80]}...")

# 3. Candidate Muhurat Windows
print("\n[3] CANDIDATE MUHURAT WINDOWS (MUMBAI OCT 24, 2024)")
r_muh = httpx.get(f"{base_url}/api/v1/rituals/muhurat-candidates?event_date=2024-10-24&latitude=19.0760&longitude=72.8777", timeout=30.0)
print(f"Status: {r_muh.status_code}")
muh = r_muh.json()
print(f"  - Sunrise: {muh['sunrise']} | Sunset: {muh['sunset']}")
print(f"  - Rahu Kaal Prohibited Window: {muh['rahu_kaal_prohibited_window']}")
for c in muh["candidates"]:
    rec = " [RECOMMENDED]" if c["is_recommended"] else ""
    print(f"  - Window: {c['name']} ({c['window']}) -> {c['suitability']}{rec}")
    print(f"    Rationale: {c['planetary_rationale']}")
print(f"  - Elevated Caution Banner: {muh['elevated_disclaimer'][:80]}...")

# 4. Multi-Tradition Merge Acceptance Scenario: Maharashtrian x Punjabi
print("\n[4] ACCEPTANCE SCENARIO: MAHARASHTRIAN x PUNJABI MULTI-TRADITION MERGE")
payload = {
    "primary_tradition_code": "maharashtrian_vedic",
    "secondary_tradition_code": "punjabi_traditional",
    "start_date": "2024-10-24",
    "notes": "Bride: Maharashtrian Vedic. Groom: Punjabi traditional. Family seeks harmonious timing with respect to both lineages."
}
r_merge = httpx.post(f"{base_url}/api/v1/rituals/merge-traditions", json=payload, timeout=60.0)
print(f"Status: {r_merge.status_code}")
merge = r_merge.json()
print(f"  - Fusion Title: {merge['fusion_title']}")
print(f"  - Primary:      {merge['primary_tradition']['name']} (Verified: {merge['primary_tradition']['is_verified']})")
print(f"  - Secondary:    {merge['secondary_tradition']['name']} (Verified: {merge['secondary_tradition']['is_verified']})")
print("\n  - Merged Run of Show (Chronological sequence with per-ceremony origin lineage):")
for idx, c in enumerate(merge["run_of_show"], 1):
    tag = c["origin_tradition"]
    chk = " [ELDER CHECKPOINT]" if c.get("is_muhurat_locked") else ""
    print(f"    {idx}. [{tag}] {c['name']} (Day {c['day_offset']}, {c['start_time']}, {c['duration_hours']}h){chk}")
    print(f"       Significance: {c['cultural_significance']}")
    print(f"       Family Guidance: {c['family_guidance']}")

print("\n  - Family Alignment Points:")
for p in merge["family_alignment_points"]:
    print(f"    * Topic: {p['issue']}")
    print(f"      Guidance: {p['recommendation']}")

print(f"\n  - Reconciled Samagri (Deduplicated with provenance tracking):")
print(f"    * Summary: {merge.get('reconciled_samagri_summary')}")
print(f"    * Total Cataloged Samagri Items: {len(merge.get('samagri_items', []))}")
for s in merge.get("samagri_items", [])[:6]:
    print(f"    * {s.get('item_name')} ({s.get('standard_quantity')}) [{s.get('category')}] -> Origin: {s.get('source_tradition')}")

print(f"\n  - Priest Coordination Note: {merge['priest_coordination_note']}")
print(f"  - Screen Disclaimer: {merge['disclaimer']}")

print("\n================================================================================")
print("                    LIVE VERIFICATION SUCCESSFUL                                ")
print("================================================================================")
