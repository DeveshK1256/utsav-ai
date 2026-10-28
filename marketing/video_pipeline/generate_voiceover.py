import subprocess
import os
import json
import re

# Pipeline Configuration
PIPER_EXE = r"C:\Users\deves\AppData\Local\Programs\Python\Python314\Scripts\piper.exe"
PIPER_MODEL = r"tools\piper_models\en_US-lessac-medium.onnx"
PIPER_CONFIG = r"tools\piper_models\en_US-lessac-medium.onnx.json"
FFMPEG_EXE = r"tools\ffmpeg.exe"
OUTPUT_DIR = "video_pipeline"

# 7 Narrative Beats
# Note on pronunciation workarounds for Piper:
# - 'Utsav' is pronounced naturally as 'Oot-sav' by phonetic respelling for clear Hindi root voicing.
# - 'muhurat' is respelled as 'moo-hoo-rat' to ensure proper vowel length rather than English mangling.
# - The display text (captions) retains correct cultural orthography ('Utsav', 'muhurat').
BEATS = [
    {
        "id": "beat1_chaos",
        "title": "Chaos to Calm",
        "display_text": "Planning an Indian celebration usually means endless WhatsApp groups, scattered vendor quotes, and budget chaos. Utsav changes that completely.",
        "spoken_text": "Planning an Indian celebration usually means endless WhatsApp groups, scattered vendor quotes, and budget chaos. Oot-sav changes that completely.",
    },
    {
        "id": "beat2_onboarding",
        "title": "Guided Onboarding",
        "display_text": "In just a minute, you share your celebration type, city, guest count, and budget. Our smart planner creates a tailored foundation instantly.",
        "spoken_text": "In just a minute, you share your celebration type, city, guest count, and budget. Our smart planner creates a tailored foundation instantly.",
    },
    {
        "id": "beat3_dashboard",
        "title": "Unified Celebration Hub",
        "display_text": "Your unified dashboard brings everything together in one serene place: real-time budgets, guest coordination, and cultural milestones.",
        "spoken_text": "Your unified dashboard brings everything together in one serene place: real-time budgets, guest coordination, and cultural milestones.",
    },
    {
        "id": "beat4_budget",
        "title": "Deterministic Budget Breakdown",
        "display_text": "Every expense is tracked deterministically across catering, decor, and photography, with transparent quote comparisons and zero hidden markups.",
        "spoken_text": "Every expense is tracked deterministically across catering, decor, and photography, with transparent quote comparisons and zero hidden markups.",
    },
    {
        "id": "beat5_map",
        "title": "Nationwide Nearby Venue Map",
        "display_text": "Explore real wedding lawns and banquet halls nationwide. Our live map pinpoints authentic celebration spaces near you with zero paid placement bias.",
        "spoken_text": "Explore real wedding lawns and banquet halls nationwide. Our live map pinpoints authentic celebration spaces near you with zero paid placement bias.",
    },
    {
        "id": "beat6_muhurat",
        "title": "Auspicious Muhurat Timing",
        "display_text": "Honor traditions with confidence. Auspicious muhurat timings align your sacred rituals according to traditional calendar wisdom.",
        "spoken_text": "Honor traditions with confidence. Auspicious moo-hoo-rat timings align your sacred rituals according to traditional calendar wisdom.",
    },
    {
        "id": "beat7_invitation_cta",
        "title": "Invitation Cards & Closing",
        "display_text": "Generate beautiful bespoke invitations in English and Devanagari with one click. Welcome to mindful celebration planning with Utsav.",
        "spoken_text": "Generate beautiful bespoke invitations in English and Devanagari with one click. Welcome to mindful celebration planning with Oot-sav.",
    }
]

def format_vtt_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

def get_audio_duration(file_path: str) -> float:
    cmd = [
        FFMPEG_EXE,
        "-i", file_path,
        "-hide_banner"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    raise ValueError(f"Could not parse duration for {file_path}")

def generate_voiceover_and_metadata():
    os.makedirs(f"{OUTPUT_DIR}/beats", exist_ok=True)
    timing_data = []
    current_time = 0.0
    vtt_lines = ["WEBVTT", ""]

    print("[1/3] Generating voiceover audio for each beat via Piper TTS...")
    wav_files = []
    
    for idx, beat in enumerate(BEATS):
        beat_id = beat["id"]
        wav_path = f"{OUTPUT_DIR}/beats/{beat_id}.wav"
        
        # Run Piper TTS
        cmd = [
            PIPER_EXE,
            "-m", PIPER_MODEL,
            "-c", PIPER_CONFIG,
            "-f", wav_path
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=beat["spoken_text"])
        
        if proc.returncode != 0:
            raise RuntimeError(f"Piper failed for {beat_id}: {stderr}")
            
        dur = get_audio_duration(wav_path)
        start_time = current_time
        # Add 0.5s pause padding between beats for natural breathing and pacing
        end_time = start_time + dur
        
        timing_info = {
            "index": idx + 1,
            "id": beat_id,
            "title": beat["title"],
            "display_text": beat["display_text"],
            "spoken_text": beat["spoken_text"],
            "wav_path": wav_path,
            "duration": dur,
            "start_time": start_time,
            "end_time": end_time
        }
        timing_data.append(timing_info)
        
        # Append VTT cue
        cue_start = format_vtt_timestamp(start_time)
        cue_end = format_vtt_timestamp(end_time)
        vtt_lines.append(f"{idx + 1}")
        vtt_lines.append(f"{cue_start} --> {cue_end}")
        vtt_lines.append(beat["display_text"])
        vtt_lines.append("")
        
        current_time = end_time + 0.45  # 450ms inter-beat pause
        wav_files.append((wav_path, dur, 0.45))
        print(f"  [OK] {beat_id} ({beat['title']}): {dur:.2f}s (Cumulative: {current_time:.2f}s)")

    # Concatenate master audio track with exact silence intervals
    print("\n[2/3] Assembling master voiceover audio track via ffmpeg...")
    concat_filter = []
    inputs = []
    for i, (wpath, dur, pause) in enumerate(wav_files):
        inputs.extend(["-i", wpath])
        # Pad silence at end of each input
        concat_filter.append(f"[{i}:a]apad=pad_dur={pause}[a{i}];")
    
    filter_graph = "".join(concat_filter) + "".join(f"[a{i}]" for i in range(len(wav_files))) + f"concat=n={len(wav_files)}:v=0:a=1[outa]"
    master_wav = f"{OUTPUT_DIR}/master_voiceover.wav"
    
    cmd_mux = [
        FFMPEG_EXE, "-y",
        *inputs,
        "-filter_complex", filter_graph,
        "-map", "[outa]",
        "-ac", "2",
        "-ar", "44100",
        master_wav
    ]
    subprocess.run(cmd_mux, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    total_master_dur = get_audio_duration(master_wav)
    print(f"  [OK] Master audio generated: {master_wav} (Total Duration: {total_master_dur:.2f}s / ~{int(total_master_dur//60)}m {int(total_master_dur%60)}s)")

    # Write synced VTT file
    print("\n[3/3] Writing synchronized WebVTT captions...")
    vtt_content = "\n".join(vtt_lines)
    vtt_path = f"{OUTPUT_DIR}/utsav_demo_captions.vtt"
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt_content)
    # Also write to frontend/public/media
    with open(f"frontend/public/media/utsav_demo_captions.vtt", "w", encoding="utf-8") as f:
        f.write(vtt_content)
        
    print(f"  [OK] Saved captions to {vtt_path} and frontend/public/media/utsav_demo_captions.vtt")

    # Write timing JSON for recorder
    timing_json_path = f"{OUTPUT_DIR}/timing_manifest.json"
    manifest = {
        "total_duration": total_master_dur,
        "master_wav": master_wav,
        "beats": timing_data
    }
    with open(timing_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"  [OK] Saved timing manifest to {timing_json_path}")
    return manifest

if __name__ == "__main__":
    generate_voiceover_and_metadata()
