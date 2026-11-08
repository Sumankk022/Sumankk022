# Cristiano Ronaldo — build sources

- `wm.py`, `fetch.py`, `manifest.txt`: search/download the Wikimedia Commons media (standard thumbnail sizes, rate-limit aware) → `img/`, `vid/`, `media.json`
- `transcripts.json`: word-timed transcript of the 8 narration clips (faster-whisper small.en)
- `build_audio.py`: hook pauses, intro ident after voice 1, chapter cards, music beds with ducking, riser→impact transition before the CTA → `out/mix.wav`, `out/timeline.json`
- `engine.py` = `cat eng_head.py eng_gfx.py eng_scenes.py eng_tail.py`; render with `python3 engine.py --part i 4` (i = 0..3), stills with `--still t …`
- Music/SFX: Mixkit (mixkit.co) track ids in `build_audio.py`; fonts: @fontsource bebas-neue, oswald, playfair-display (npm)
