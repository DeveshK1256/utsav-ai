"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, Volume2, VolumeX, Subtitles } from "lucide-react";

export function WalkthroughVideoPlayer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    // Respect prefers-reduced-motion: if user prefers reduced motion, never autoplay
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const storedMotion = localStorage.getItem("utsav-reduced-motion");
    const prefersReduced = storedMotion === "reduced" || motionQuery.matches;

    const video = videoRef.current;
    if (!video) return;

    if (prefersReduced) {
      video.autoplay = false;
      video.pause();
    } else {
      // Autoplay muted by default for smooth experience if user hasn't requested reduced motion
      video.muted = true;
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsPlaying(true);
          })
          .catch(() => {
            // Autoplay prevented by browser policy; user clicks poster
            setIsPlaying(false);
          });
      }
    }

    // Set caption track mode to showing
    if (video.textTracks && video.textTracks[0]) {
      video.textTracks[0].mode = "showing";
    }
  }, []);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    setHasInteracted(true);

    if (video.paused) {
      video.play().then(() => setIsPlaying(true));
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  };

  const toggleCaptions = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video || !video.textTracks) return;
    const track = video.textTracks[0];
    if (!track) return;
    const newMode = track.mode === "showing" ? "hidden" : "showing";
    track.mode = newMode;
    setCaptionsEnabled(newMode === "showing");
  };

  return (
    <section
      aria-label="Product Walkthrough Video"
      className="max-w-5xl mx-auto px-4 sm:px-6 my-16"
    >
      <div className="text-center mb-8">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-500/20">
          Real Product Demonstration
        </span>
        <h2 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-white mt-3">
          See Utsav in Action
        </h2>
        <p className="text-sm sm:text-base text-stone-600 dark:text-stone-300 max-w-2xl mx-auto mt-2">
          A real walkthrough of our live celebration hub — from planning chaos
          to transparent budgets, nationwide venue discovery, and auspicious
          timings.
        </p>
      </div>

      <div className="relative rounded-2xl overflow-hidden border border-stone-200/90 dark:border-stone-800 bg-stone-900 shadow-2xl group aspect-video">
        {hasError ? (
          <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-stone-950 text-stone-300">
            <p className="text-base font-medium">
              Video could not be loaded directly.
            </p>
            <p className="text-xs text-stone-500 mt-2 max-w-md">
              You can experience the interactive walkthrough live on the
              platform by starting an event intake.
            </p>
            <a
              href="/onboarding"
              className="mt-4 px-5 py-2.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-[#8B1E28] text-white hover:bg-[#A32431] transition-all"
            >
              Start Live Onboarding
            </a>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              playsInline
              preload="metadata"
              poster="/media/utsav_intro_poster.jpg"
              onClick={togglePlay}
              onEnded={() => setIsPlaying(false)}
              onError={() => setHasError(true)}
              className="w-full h-full object-cover cursor-pointer"
            >
              <source
                src="/media/utsav_intro_walkthrough.mp4"
                type="video/mp4"
              />
              <track
                kind="captions"
                src="/media/utsav_demo_captions.vtt"
                srcLang="en"
                label="English"
                default
              />
              Your browser does not support the video tag.
            </video>

            {/* Poster Overlay Play Button when Paused */}
            {!isPlaying && (
              <div
                onClick={togglePlay}
                className="absolute inset-0 bg-black/40 backdrop-blur-[2px] flex flex-col items-center justify-center cursor-pointer transition-opacity duration-300"
              >
                <button
                  type="button"
                  aria-label="Play video walkthrough"
                  className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[#8B1E28] text-white flex items-center justify-center shadow-lg hover:scale-110 active:scale-95 transition-transform"
                >
                  <Play className="w-8 h-8 sm:w-10 sm:h-10 ml-1 fill-white" />
                </button>
                <span className="mt-4 text-xs sm:text-sm font-semibold tracking-wide text-white uppercase drop-shadow">
                  Watch 60-Second Walkthrough
                </span>
              </div>
            )}

            {/* Custom Control Overlay Bar */}
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 flex items-center justify-between text-white opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={togglePlay}
                  aria-label={isPlaying ? "Pause" : "Play"}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={toggleMute}
                  aria-label={isMuted ? "Unmute voiceover" : "Mute voiceover"}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors flex items-center gap-1.5 text-xs"
                >
                  {isMuted ? (
                    <VolumeX className="w-5 h-5 text-amber-400" />
                  ) : (
                    <Volume2 className="w-5 h-5" />
                  )}
                  <span className="hidden sm:inline font-mono">
                    {isMuted ? "Unmute" : "Voice on"}
                  </span>
                </button>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <button
                  type="button"
                  onClick={toggleCaptions}
                  aria-label="Toggle captions"
                  className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${
                    captionsEnabled
                      ? "bg-amber-500/30 text-amber-300"
                      : "hover:bg-white/20 text-stone-300"
                  }`}
                >
                  <Subtitles className="w-5 h-5" />
                  <span className="hidden sm:inline font-mono">CC</span>
                </button>
                <span className="font-mono text-stone-300 text-[11px]">
                  1:00
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-xs text-stone-700 dark:text-stone-300 font-medium px-1">
        <p>
          Recorded live against Utsav v1.0. Audio voiceover generated via local
          Piper TTS with verified phonetic timing.
        </p>
        <span className="font-mono text-amber-800 dark:text-amber-300 font-medium">
          Captions: WebVTT Synced
        </span>
      </div>
    </section>
  );
}
