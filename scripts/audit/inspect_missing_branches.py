import json

d = json.load(open('cov.json'))
targets = [
    'services\\replanning_service.py',
    'services\\discovery_service.py',
    'services\\vibe_aggregation_engine.py',
    'services\\whatsapp\\webhook_service.py',
    'api\\v1\\guests.py',
    'services\\dag_scheduler.py',
    'services\\invitation_renderer.py',
    'api\\v1\\invitations.py',
    'api\\v1\\quotes.py',
    'services\\vibe_service.py',
    'services\\budget_rescaling_engine.py',
    'services\\whatsapp\\faq_bot.py',
]

for t in targets:
    matching = [k for k in d['files'] if t in k]
    if not matching:
        continue
    k = matching[0]
    info = d['files'][k]
    mb = info.get('missing_branches', [])
    ml = info.get('missing_lines', [])
    print(f"\n==========================================")
    print(f"{t}: {len(mb)} missing branches, {len(ml)} missing lines")
    print(f"Missing branches: {mb}")
