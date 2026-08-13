# 0009: Server-synchronized sound fade

Branch: `task/sound-fade`
Status: Completed

## Goal

Add a `Fade 3s` action next to `Silence` that fades every game-controlled sound on all connected clients and ends in an authoritative stop without letting an obsolete fade stop a later sound.

## Accepted behavior

- Fade lasts exactly three seconds and affects shared managed audio, one-shot game effects/signals, and the wheel loop.
- Loudness falls uniformly from 0 to -60 dB (an exponential amplitude curve), so the sound is already effectively silent before the final Stop instead of remaining loud through most of the interval.
- Private admin media preview is not shared game audio and remains outside this action.
- The button is immediate, sits next to `Silence` in Live Ops, and writes one admin log entry.
- A client reconnecting during an active fade receives its current progress instead of restarting from full volume.
- Master volume remains independent: effective volume is master volume multiplied by the fade level and, for the wheel, its existing intrinsic fade level.
- A later Play, Stop, Silence, wheel start, game effect, or repeated Fade supersedes the older fade. Its delayed completion must become a no-op.
- A repeated Fade continues smoothly from the current level rather than jumping back to full volume.
- A new sound-producing command after Fade restores the shared fade level to 100% before starting the sound.

## Implementation decisions

- Keep the existing flat `state_update` contract unchanged. Extend the already reconnect-aware `settings_update` payload with a server-authoritative `sound_control` snapshot.
- `sound_control` carries a monotonically increasing generation, optional fade start/duration, starting level, and a dynamic server timestamp. Clients combine server progress with local time since receipt.
- Backend sound commands synchronously advance the generation before their first network emit. Fade completion checks the captured generation before stopping anything.
- Fade completion stops shared media through its existing authoritative playback state and emits the existing immediate `stop_sound` command for effects and the wheel.
- Frontend computes one shared fade multiplier and feeds it to `useGameSound` and every `SynchronizedAudio`; individual components do not own competing emergency-fade timers.
- Backend and frontend use the same 60 dB curve; the browser updates it every 25 ms.

## Out of scope

- Fading private preview controls, per-sound mixers, user-specific volume, persistence across backend restart, audio duration/ended detection, video, or changing the existing wheel animation duration.

## Verification

- Pure backend tests for progress math, repeated fade, generation invalidation, and completion guards.
- Handler tests for admin-only access, reconnect snapshot, all-sound stop, and races with later Play/Silence/spin/effect commands.
- Frontend pure tests for timestamp/multiplier math plus hook-level integration through buildable components.
- Two-browser smoke with shared question audio, an effect, a spinning wheel, reconnect during fade, repeated Fade, Fade→Play, and Fade→Silence.

## Local verification status

Passed locally:

- `python3 -W error -m pytest -q`: 113 tests;
- `npm test`: 13 assertions across playback, Live Ops, and sound-fade helpers;
- `npm run build`;
- clean `npm ci` and `npm audit`: 0 vulnerabilities;
- `docker compose config --quiet` and both development image builds;
- Python 3.14 container: `pip check` and 113 tests;
- Node 24 container: 13 frontend assertions and production build.

Remote verification and acceptance:

- all three GitHub Actions jobs passed on `bdd225e`;
- the focused two-browser smoke passed for shared media, effects, wheel sound, reconnect, repeated Fade, Fade→Play, and Fade→Silence;
- the perceptual 0 to -60 dB curve was accepted after a browser check with the wheel sound.
