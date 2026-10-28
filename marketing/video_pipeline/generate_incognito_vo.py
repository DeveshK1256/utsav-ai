import subprocess
import os

piper_exe = r"C:\Users\deves\AppData\Local\Programs\Python\Python314\Scripts\piper.exe"
model = r"tools\piper_models\en_US-lessac-medium.onnx"
config = r"tools\piper_models\en_US-lessac-medium.onnx.json"
ffmpeg_exe = r"tools\ffmpeg.exe"

os.makedirs("video_pipeline/incognito_vo", exist_ok=True)

lines = [
    ("vo1_incognito", "Opening an incognito browser window and navigating directly to our deployed Netlify production app at utsav-ai.netlify.app."),
    ("vo2_landing", "The live application loads with an interactive 3D Diya, cultural aesthetics, and our core philosophy: turning Indian wedding chaos into calm."),
    ("vo3_onboarding", "In onboarding, we specify the celebration type, host city like Jaipur, guest count, and rupee budget to generate an authentic plan."),
    ("vo4_dashboard", "The unified celebration dashboard provides deterministic budget math with zero hallucinations, transparent quote audits, and live venue mapping."),
    ("vo5_invitation", "Finally, our invitation engine renders authentic Devanagari typography with sacred shlokas and zero tofu boxes, ready for 300 DPI print export.")
]

for vid, text in lines:
    out_wav = f"video_pipeline/incognito_vo/{vid}.wav"
    cmd = [piper_exe, "--model", model, "--config", config, "--output_file", out_wav]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    
    # get duration
    dur_cmd = [ffmpeg_exe, "-i", out_wav]
    res = subprocess.run(dur_cmd, capture_output=True, text=True)
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            print(f"{vid}: {line.strip()}")

print("All incognito voiceover clips generated.")
