# Stick-figure cartoon reel series

`the_last_coffee.mp4`: vertical 1080×1920, 30 fps, 30 s. Flat-vector stick-figure style, with background music, sound effects and wordless reaction voices. There is no dialogue or narration.

**Story:** It's 3 AM and a tired coder reaches for coffee, but the mug is empty. The coffee machine is out too ("EMPTY"). He gets an idea and grabs an energy drink from the desk drawer, shakes it, and it sprays all over his face. The drink makes him hyper, he finishes the build at 100%, then falls asleep on the keyboard as the sun comes up.

Everything is made from code, so the video uses no stock assets:
- `render.py` draws the animation: rig, camera moves and effects (PIL, 2× supersampled).
- `audio.py` synthesizes the sound: lo-fi, sneaky, upbeat, chiptune and lullaby music sections, the SFX, and the reaction voices made with formant synthesis.
- `build.sh` renders and muxes the final MP4 with `./build.sh`. It needs Python 3 with Pillow and numpy, plus ffmpeg.

## Episodes 2–6

Same character, with a different outfit and location in each. All are 30 s, vertical 1080×1920, with background music, sound effects and reaction voices only.

| File | Outfit | Location | Story |
|---|---|---|---|
| `ep2_sandcastle.mp4` | Red tank top, shorts, sunglasses | Beach | Builds a sandcastle and a giant wave washes it away. Finds treasure underneath, then a crab pinches his nose. |
| `ep3_pancake.mp4` | Chef coat, chef hat, red neckerchief | Kitchen | Flips a pancake that sticks to the ceiling, and it later drops onto his face. He eats his way out. |
| `ep4_rainyday.mp4` | Yellow raincoat with hood, red boots | Rainy city street | Wind turns his umbrella inside out. He dances in a puddle, a car soaks him, then a rainbow appears and he sneezes. |
| `ep5_legday.mp4` | Orange tank top, headband, wristbands | Gym | Lifts a huge weight, falls over, switches to a tiny pink dumbbell and drops it on his toe. |
| `ep6_snowman.mp4` | Purple puffer jacket, beanie, scarf | Snowy park | Builds a snowman, gets hit by snowballs from someone off-screen, and gets rolled up inside a giant snowball. |

- `engine.py`: shared code. It has outfit-driven character drawing, keyframe pose tracks, effects (particles, rain, snow, stars) and audio helpers (reaction voices and SFX).
- `epN_*.py`: one file per episode, covering background, story, camera and sound.
- `./build_series.sh [ep...]` renders all episodes, or only the ones you name. To preview a few frames, run `python3 ep3_pancake.py preview <dir> 7.5,20.3`.
