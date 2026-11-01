# The Last Coffee — 30s cartoon reel

`the_last_coffee.mp4`: vertical 1080×1920, 30 fps, 30 s. Flat-vector stick-figure style, with background music, sound effects and wordless reaction voices. There is no dialogue or narration.

**Story:** It's 3 AM and a tired coder reaches for coffee, but the mug is empty. The coffee machine is out too ("EMPTY"). He gets an idea and grabs an energy drink from the desk drawer, shakes it, and it sprays all over his face. The drink makes him hyper, he finishes the build at 100%, then falls asleep on the keyboard as the sun comes up.

Everything is made from code, so the video uses no stock assets:
- `render.py` draws the animation: rig, camera moves and effects (PIL, 2× supersampled).
- `audio.py` synthesizes the sound: lo-fi, sneaky, upbeat, chiptune and lullaby music sections, the SFX, and the reaction voices made with formant synthesis.
- `build.sh` renders and muxes the final MP4 with `./build.sh`. It needs Python 3 with Pillow and numpy, plus ffmpeg.
