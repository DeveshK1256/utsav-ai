import urllib.request
import urllib.error
import json
import sys

NETLIFY_URL = 'https://utsav-ai.netlify.app'

def main():
    print(f"Simulating fresh host journey on live Netlify site ({NETLIFY_URL})...")

    # 1. Onboarding Wizard intake generation
    intake_payload = json.dumps({
        'name': 'Pooja & Rohan Vivah',
        'host_name': 'Pooja Sharma',
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
        print(f"1. Onboarding complete: event_id={event_id}, owner_token_present={bool(owner_token)} (len={len(owner_token) if owner_token else 0})")
        assert owner_token, 'No owner_token returned!'

    # 2. Host performs Compose Step A (Venue Selection) with X-Event-Owner-Token
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
        meta = res2.get('metadata_json') or {}
        print(f"2. Compose Step A (Venue skip) status={resp.status}: compose_celebration state={bool(meta.get('compose_celebration'))}")
        assert resp.status == 200

    # 3. Host performs Compose Step B (Muhurat Timing) with X-Event-Owner-Token
    compose_b_payload = json.dumps({
        'step': 'invitation',
        'muhurat_time': '11:30 AM - 01:00 PM (Abhijit Muhurat)',
        'muhurat_notes': 'Confirmed on Netlify'
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
        print(f"3. Compose Step B (Muhurat confirm) status={resp.status}")
        assert resp.status == 200

    # 4. Host triggers Invitation Generation with X-Event-Owner-Token
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
        res4 = json.loads(resp.read().decode())
        assert resp.status in (200, 201), f"Expected 200/201, got {resp.status}"
        assert 'cards' in res4 and len(res4['cards']) > 0, f"Expected non-empty cards list: {res4}"
        card = res4['cards'][0]
        card_id = card.get('id')
        print(f"4. Invitation Generation status={resp.status}: card_id={card_id} (cards_count={len(res4['cards'])}, total_generated={res4.get('total_generated')})")
        assert card_id is not None and isinstance(card_id, str) and len(card_id) == 36, f"Invalid card_id: {card_id}"
        assert f"/invitations/{card_id}/download?format=png" in card.get('png_download_url', ''), f"Invalid png_download_url: {card.get('png_download_url')}"

    # 5. Verify that mutating WITHOUT token is blocked with 403
    req_unauth = urllib.request.Request(
        f'{NETLIFY_URL}/api/v1/events/{event_id}/compose',
        data=compose_a_payload,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        urllib.request.urlopen(req_unauth)
        raise AssertionError('Unauthenticated request succeeded!')
    except urllib.error.HTTPError as e:
        print(f"5. Unauthenticated mutation correctly blocked with HTTP {e.code}: {e.read().decode()}")
        assert e.code == 403

    # Clean up test event with authenticated DELETE
    req_del = urllib.request.Request(
        f'{NETLIFY_URL}/api/v1/events/{event_id}',
        method='DELETE',
        headers={'X-Event-Owner-Token': owner_token, 'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req_del) as resp:
        print(f"6. Cleanup authenticated DELETE status={resp.status}")
        assert resp.status == 200

    print("\nSUCCESS: Real host journey verified end-to-end on live Netlify site without 403 errors!")
    return True

if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
