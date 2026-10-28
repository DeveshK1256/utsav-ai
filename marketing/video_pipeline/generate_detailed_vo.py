import subprocess
import os

piper_exe = r"C:\Users\deves\AppData\Local\Programs\Python\Python314\Scripts\piper.exe"
model = r"tools\piper_models\en_US-lessac-medium.onnx"
config = r"tools\piper_models\en_US-lessac-medium.onnx.json"
ffmpeg_exe = r"tools\ffmpeg.exe"

os.makedirs("video_pipeline/detailed_vo", exist_ok=True)

# 7 In-Depth Walkthrough Beats
beats_vo = [
    ("d1_incognito", "Welcome to the complete production walkthrough of Utsav. We begin by opening an incognito browser window and navigating directly to our deployed Netlify web app at utsav-ai.netlify.app."),
    ("d2_landing", "The live application immediately welcomes hosts with an interactive 3-D Diya and our core philosophy: replacing chaotic spreadsheets and endless WhatsApp threads with serene, culture-native orchestration."),
    ("d3_onboarding", "In guided onboarding, hosts configure their celebration in under a minute—choosing celebration type, entering their host city like Jaipur, guest count, and rupee budget to generate a culturally grounded foundation."),
    ("d4_dashboard", "The unified celebration hub brings every facet of an Indian wedding into one single source of truth—real-time budgets, guest coordination, and sacred ritual schedules."),
    ("d5_quotes", "Unlike generic AI models that invent fake rupee numbers, Utsav tracks every expense deterministically across catering, decor, and photography—with transparent quote comparisons and zero hidden markups."),
    ("d6_map_muhurat", "Our live map pinpoints authentic celebration spaces nationwide using OpenStreetMap with zero paid placement bias, while auspicious muhurat calculations align sacred rituals with traditional calendar wisdom."),
    ("d7_invitations_outro", "Finally, our bespoke invitation studio renders authentic Devanagari typography and Sanskrit shlokas with zero tofu boxes, exportable at 300 DPI. Built with Google Gemini for Prompt Wars Virtual!")
]

for vid, text in beats_vo:
    out_wav = f"video_pipeline/detailed_vo/{vid}.wav"
    cmd = [piper_exe, "--model", model, "--config", config, "--output_file", out_wav]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    
    # get duration
    dur_cmd = [ffmpeg_exe, "-i", out_wav]
    res = subprocess.run(dur_cmd, capture_output=True, text=True)
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            print(f"{vid}: {line.strip()}")

print("All 7 detailed voiceover clips generated successfully.")
