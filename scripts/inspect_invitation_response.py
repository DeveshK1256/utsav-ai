import urllib.request
import json
import sys

NETLIFY_URL = "https://utsav-ai.netlify.app"

def main():
    print("Testing live endpoint POST /events/{id}/invitations/generate...")
    # 1. Create test event via intake/generate
    intake_payload = json.dumps({
        'name': 'Card ID Anomaly Verification Wedding',
        'host_name': 'Anomaly Verification Host',
        'phone_number': '+919822334455',
        'event_type': 'wedding',
        'tradition_code': 'marwari_traditional',
        'guest_count': 200,
        'total_budget': 1500000.0,
        'city': 'Jaipur',
        'pincode': '302001',
        'start_date': '2027-02-14',
        'end_date': '2027-02-15'
    }).encode('utf-8')

    req1 = urllib.request.Request(
        f'{NETLIFY_URL}/api/v1/intake/generate',
        data=intake_payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req1) as resp:
        plan = json.loads(resp.read().decode())
        event_id = plan['event_id']
        owner_token = plan.get('owner_token')
        print(f"1. Onboarding complete: event_id={event_id}, owner_token={owner_token[:8]}...")

    try:
        # 2. Host performs Compose Step A (Venue Selection: skip)
        compose_a_payload = json.dumps({
            'step': 'venue',
            'skip_venue': True
        }).encode('utf-8')
        req2 = urllib.request.Request(
            f'{NETLIFY_URL}/api/v1/events/{event_id}/compose',
            data=compose_a_payload,
            headers={
                'Content-Type': 'application/json',
                'X-Event-Owner-Token': owner_token,
                'User-Agent': 'Mozilla/5.0'
            }
        )
        with urllib.request.urlopen(req2) as resp:
            res2 = json.loads(resp.read().decode())
            print(f"2. Compose Step A (Venue Skip) status={resp.status}")

        # 3. Host performs Compose Step B (Muhurat Timing Confirmation)
        compose_b_payload = json.dumps({
            'step': 'muhurat',
            'muhurat_selection': {
                'sub_event_id': None,
                'muhurat_time': '10:15 AM - 12:30 PM',
                'confirmed': True
            }
        }).encode('utf-8')
        req3 = urllib.request.Request(
            f'{NETLIFY_URL}/api/v1/events/{event_id}/compose',
            data=compose_b_payload,
            headers={
                'Content-Type': 'application/json',
                'X-Event-Owner-Token': owner_token,
                'User-Agent': 'Mozilla/5.0'
            }
        )
        with urllib.request.urlopen(req3) as resp:
            res3 = json.loads(resp.read().decode())
            print(f"3. Compose Step B (Muhurat Confirmation) status={resp.status}")

        # 4. Host generates invitation card
        invitation_payload = json.dumps({
            'layout_variant': 'classic_arch',
            'wording_variant_index': 0
        }).encode('utf-8')
        req4 = urllib.request.Request(
            f'{NETLIFY_URL}/api/v1/events/{event_id}/invitations/generate',
            data=invitation_payload,
            headers={
                'Content-Type': 'application/json',
                'X-Event-Owner-Token': owner_token,
                'User-Agent': 'Mozilla/5.0'
            }
        )
        with urllib.request.urlopen(req4) as resp:
            status = resp.status
            raw_body = resp.read().decode('utf-8')
            parsed = json.loads(raw_body)
            print(f"\n================ RAW JSON RESPONSE BODY (HTTP {status}) ================")
            print(json.dumps(parsed, indent=2))
            print("========================================================================\n")

            print(f"Top-level keys in response: {list(parsed.keys())}")
            has_top_level_id = "id" in parsed
            print(f"Is 'id' in top-level keys? {has_top_level_id}")
            print(f"Is 'cards' in top-level keys? {'cards' in parsed}")
            if "cards" in parsed and len(parsed["cards"]) > 0:
                first_card = parsed["cards"][0]
                print(f"First card keys: {list(first_card.keys())}")
                print(f"First card 'id': {first_card.get('id')}")
                print(f"First card 'png_download_url': {first_card.get('png_download_url')}")
                print(f"First card 'pdf_download_url': {first_card.get('pdf_download_url')}")

    finally:
        # Clean up test event with authenticated DELETE
        req_del = urllib.request.Request(
            f'{NETLIFY_URL}/api/v1/events/{event_id}',
            method='DELETE',
            headers={'X-Event-Owner-Token': owner_token, 'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req_del) as resp_del:
            print(f"Cleaned up event: {resp_del.status}")

if __name__ == '__main__':
    main()
