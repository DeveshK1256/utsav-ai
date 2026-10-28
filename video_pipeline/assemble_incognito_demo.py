import os
import subprocess
import json

ffmpeg_exe = r"tools\ffmpeg.exe"
clips_dir = "video_pipeline/clips_incognito"
trimmed_dir = "video_pipeline/trimmed_incognito"
vo_dir = "video_pipeline/incognito_vo"
output_dir = "brag-output"
music_path = r"C:\Users\deves\.gemini\config\plugins\brag\skills\brag\assets\music\happy-beats-business-moves-vol-1-by-ende-dot-app.mp3"

os.makedirs(trimmed_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs("frontend/public/media", exist_ok=True)

# 1. Clip timing configurations
beats = [
    {"id": "beat1_incognito_paste", "ss": 0.0, "dur": 8.2, "vo": "vo1_incognito.wav", "vo_delay": 400},
    {"id": "beat2_landing_3d", "ss": 1.5, "dur": 8.5, "vo": "vo2_landing.wav", "vo_delay": 400},
    {"id": "beat3_onboarding", "ss": 0.5, "dur": 8.5, "vo": "vo3_onboarding.wav", "vo_delay": 400},
    {"id": "beat4_dashboard_budget", "ss": 0.5, "dur": 9.2, "vo": "vo4_dashboard.wav", "vo_delay": 400},
    {"id": "beat5_invitation_export", "ss": 0.5, "dur": 10.2, "vo": "vo5_invitation.wav", "vo_delay": 400}
]

trimmed_files = []
total_timeline_ms = 0
vo_mix_inputs = []
vo_filter_delays = []

for i, b in enumerate(beats):
    in_webm = os.path.join(clips_dir, f"{b['id']}.webm")
    out_mp4 = os.path.join(trimmed_dir, f"{b['id']}.mp4")
    
    # Standardize video to 1920x1080 30fps
    cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(b["ss"]),
        "-t", str(b["dur"]),
        "-i", in_webm,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-an",
        out_mp4
    ]
    subprocess.run(cmd, check=True)
    trimmed_files.append(out_mp4)
    print(f"Trimmed {b['id']} -> {b['dur']}s")

    # Audio delay calculation
    current_vo_delay = int(total_timeline_ms + b["vo_delay"])
    vo_path = os.path.join(vo_dir, b["vo"])
    vo_mix_inputs.extend(["-i", vo_path])
    vo_filter_delays.append(f"[{i}:a]adelay={current_vo_delay}|{current_vo_delay}[a{i}]")
    
    total_timeline_ms += int(b["dur"] * 1000)

total_dur_sec = total_timeline_ms / 1000.0
print(f"Total video duration: {total_dur_sec:.2f}s")

# 2. Concat video clips
concat_list = "video_pipeline/concat_incognito.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for tf in trimmed_files:
        abs_p = os.path.abspath(tf).replace("\\", "/")
        f.write(f"file '{abs_p}'\n")

raw_video = "video_pipeline/incognito_video_concat.mp4"
cmd_concat = [
    ffmpeg_exe, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_list,
    "-c", "copy",
    raw_video
]
subprocess.run(cmd_concat, check=True)
print("Concatenated video clips successfully.")

# 3. Assemble voiceover track
vo_labels = "".join(f"[a{i}]" for i in range(len(beats)))
filter_graph = f"{';'.join(vo_filter_delays)};{vo_labels}amix=inputs={len(beats)}:dropout_transition=0:normalize=0[vo]"

vo_track = "video_pipeline/incognito_vo_master.m4a"
cmd_vo = [
    ffmpeg_exe, "-y",
    *vo_mix_inputs,
    "-filter_complex", filter_graph,
    "-map", "[vo]",
    "-c:a", "aac",
    "-b:a", "192k",
    vo_track
]
subprocess.run(cmd_vo, check=True)
print("Master voiceover track assembled.")

# 4. Mix voiceover with background music (ducked)
soundtrack = "video_pipeline/incognito_soundtrack.m4a"
fade_start = max(0, total_dur_sec - 2.5)
cmd_soundtrack = [
    ffmpeg_exe, "-y",
    "-i", vo_track,
    "-ss", "0", "-t", str(total_dur_sec),
    "-i", music_path,
    "-filter_complex",
    f"[1:a]volume=0.20,afade=t=out:st={fade_start:.2f}:d=2.0[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[outa]",
    "-map", "[outa]",
    "-c:a", "aac",
    "-b:a", "192k",
    soundtrack
]
subprocess.run(cmd_soundtrack, check=True)
print("Master soundtrack assembled.")

# 5. Final Mux Video + Soundtrack with +faststart
final_mp4 = os.path.join(output_dir, "utsav_deployed_incognito_demo.mp4")
cmd_mux = [
    ffmpeg_exe, "-y",
    "-i", raw_video,
    "-i", soundtrack,
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "20",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    "-shortest",
    final_mp4
]
subprocess.run(cmd_mux, check=True)
print(f"Final MP4 created: {final_mp4} (Size: {os.path.getsize(final_mp4)/(1024*1024):.2f} MB)")

# 6. Extract high-res poster and bake frame 0
poster_jpg = os.path.join(output_dir, "utsav_deployed_incognito_demo.jpg")
cmd_poster = [
    ffmpeg_exe, "-y",
    "-ss", "00:00:02.500",
    "-i", final_mp4,
    "-vframes", "1",
    "-q:v", "2",
    poster_jpg
]
subprocess.run(cmd_poster, check=True)
print(f"Extracted poster frame: {poster_jpg}")

# Bake poster as frame 0
baked_mp4 = os.path.join(output_dir, "utsav_deployed_incognito_demo.poster.mp4")
cmd_bake = [
    ffmpeg_exe, "-y",
    "-i", final_mp4,
    "-i", poster_jpg,
    "-filter_complex", "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]",
    "-map", "[v]",
    "-map", "0:a?",
    "-c:v", "libx264",
    "-crf", "20",
    "-preset", "fast",
    "-pix_fmt", "yuv420p",
    "-c:a", "copy",
    "-movflags", "+faststart",
    baked_mp4
]
subprocess.run(cmd_bake, check=True)
if os.path.exists(baked_mp4):
    os.replace(baked_mp4, final_mp4)
    print("Poster baked into frame 0.")

# 7. Copy to public/media for web deployment
public_mp4 = "frontend/public/media/utsav_deployed_incognito_demo.mp4"
public_jpg = "frontend/public/media/utsav_deployed_incognito_demo.jpg"
subprocess.run(["cmd", "/c", "copy", "/y", final_mp4, public_mp4], check=True)
subprocess.run(["cmd", "/c", "copy", "/y", poster_jpg, public_jpg], check=True)
print(f"Exported to web assets: {public_mp4} and {public_jpg}")
