# 0012: Game over

Branch: `task/game-over`
Status: Completed

## Goal

Finish a game explicitly after one side reaches six points, while preserving the current answer-review step and giving every connected/reconnecting client a stable final screen.

## Current context

- Scoring already leaves the game in `POST_ROUND`, including on the sixth point.
- `transition_end_round` currently always advances a blitz part or returns to `PRE_ROUND`; a later spin is only rejected by a score guard.
- The existing score-board assets include every 0–6 score combination and `frontend/public/sounds/final.mp3` already exists.
- Reset returns the loaded game to `PRE_ROUND`, clears progress, and retains the loaded pack and connected players.

## Accepted behavior

- Add the explicit public phase `GAME_OVER`.
- Awarding the sixth point still enters `POST_ROUND` and keeps question/answer/commentary available to the host.
- In `POST_ROUND`, if either side has six points, the normal end-round action becomes `Завершить игру` and enters `GAME_OVER`; this takes precedence over an inconsistent pending blitz-part advance.
- Entering `GAME_OVER` clears round, timer, shared media, media tokens, admin question, and active wheel context; it stops older sounds before broadcasting `final.mp3`.
- All clients show the existing final score board plus one shared final card naming the winner. Reconnect restores the final screen from authoritative state but does not replay the one-shot final sound.
- Normal wheel and phase actions are unavailable in `GAME_OVER`. Director sound controls, player management, logs, and collapsed Live Ops recovery remain available to the host.
- The reset action is labelled `Новая игра` in `GAME_OVER`, stops final audio, resets to `PRE_ROUND`, and retains connected players and the loaded pack.
- Backend phase guards remain authoritative; the frontend is not the only protection against actions after game end.

## Implementation decisions

- Extend the existing flat `state_update.phase` compatibility field with `GAME_OVER`; do not add a separate winner field because the winner is derived unambiguously from the authoritative score.
- Keep finalization in the synchronous transition layer and deliver cleanup/sound through `TransitionEffects`.
- Add a dedicated shared `FinalScreen` component; keep `ScoreBoard` as the graphical source of the final score.
- Keep exceptional Live Ops recovery available instead of treating it as normal game flow.

## Out of scope

- Match history, persistence/restart recovery, returning players to `LOGIN`, rematches with a new pack, ceremonies/animation/confetti, automatic final-sound replay on reconnect, intro, or public deployment changes.

## Verification

- Transition tests for sixth point → `POST_ROUND`, final action → `GAME_OVER`, cleanup/effects, TV and experts wins, blitz precedence, normal non-final round behavior, and rejected post-final actions.
- Handler test for authoritative final state plus stop/final sound events.
- Frontend helper/build coverage for winner presentation and final-phase rendering.
- Two-browser smoke for sixth point, answer review, explicit final action, score/winner display, final sound, reconnect, blocked normal controls, and new-game reset.

## Local verification status

Implemented locally:

- explicit `GAME_OVER` state and atomic end-round finalization after a six-point `POST_ROUND`;
- cleanup of round/media/token/timer/wheel/admin-question context plus stop-then-final sound effects;
- score guards, including rejection of the impossible recovery score 6:6 until it is repaired;
- shared final score/winner screen and reconnect rendering;
- game-over host UI with normal controls removed and `Новая игра` reset retained;
- reset stops final audio while retaining connected players and the loaded pack.

Passed locally:

- `python3 -m pytest -q`: 118 backend tests;
- `python3 -W error -m pytest -q`: 118 backend tests;
- `npm test`: 20 frontend tests, including 3 game-over presentation tests;
- `npm run build`;
- `docker compose config --quiet`.

Remote verification and acceptance:

- backend, frontend, and Compose GitHub Actions jobs passed on `1e8a2aa`;
- the focused two-browser game-over smoke passed and the final flow was accepted.
