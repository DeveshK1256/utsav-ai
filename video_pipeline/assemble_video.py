import json
import subprocess
import os

FFMPEG = r"tools\ffmpeg.exe"
MANIFEST = "video_pipeline/timing_manifest.json"

with open(MANIFEST, "r", encoding="utf-8") as f:
    data = json.load(f)

beats = data["beats"]
master_wav = data["master_wav"]
total_dur = data["total_duration"]

print(f"Master voiceover duration: {total_dur:.2f}s")
os.makedirs("video_pipeline/trimmed", exist_ok=True)

# 1. Trim and standardize each clip to exact (duration + 0.45s) at 1280x720, 30fps
trimmed_files = []
for beat in beats:
    bid = beat["id"]
    in_webm = f"video_pipeline/clips/{bid}.webm"
    out_mp4 = f"video_pipeline/trimmed/{bid}.mp4"
    dur = beat["duration"] + 0.45
    
    cmd = [
        FFMPEG, "-y",
        "-ss", "0",
        "-t", f"{dur:.3f}",
        "-i", in_webm,
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-an",
        out_mp4
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    trimmed_files.append(out_mp4)
    print(f"Trimmed {bid} to {dur:.2f}s")

# 2. Concat trimmed video files
concat_list = "video_pipeline/concat_list.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for tf in trimmed_files:
        abs_p = os.path.abspath(tf).replace("\\", "/")
        f.write(f"file '{abs_p}'\n")

concat_video = "video_pipeline/concat_video.mp4"
cmd_concat = [
    FFMPEG, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_list,
    "-c", "copy",
    concat_video
]
subprocess.run(cmd_concat, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print("Concatenated video clips.")

# 3. Mux video with master voiceover and compress to web-optimized MP4 (< 10MB)
final_mp4 = "frontend/public/media/utsav_intro_walkthrough.mp4"
cmd_final = [
    FFMPEG, "-y",
    "-i", concat_video,
    "-i", master_wav,
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "24",
    "-c:a", "aac",
    "-b:a", "128k",
    "-movflags", "+faststart",
    "-shortest",
    final_mp4
]
subprocess.run(cmd_final, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
file_size_mb = os.path.getsize(final_mp4) / (1024 * 1024)
print(f"[SUCCESS] Final assembled walkthrough video: {final_mp4}")
print(f"File Size: {file_size_mb:.2f} MB")

# 4. Generate poster frame image from Beat 1 (first frame)
poster_jpg = "frontend/public/media/utsav_intro_poster.jpg"
cmd_poster = [
    FFMPEG, "-y",
    "-ss", "00:00:01.500",
    "-i", final_mp4,
    "-vframes", "1",
    "-q:v", "2",
    poster_jpg
]
subprocess.run(cmd_poster, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"[SUCCESS] Extracted poster frame: {poster_jpg}")
