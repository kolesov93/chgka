import volchok as vlk
import common
import pyglet
from pyglet.window import key
import logging
import random

logger = logging.getLogger('game')
logger.setLevel(logging.DEBUG)

FRAME_UPDATE = 0.02
VELOCITY_DELTA = 0.01

class RoundState:
    INIT = -1
    CAN_START_ARROW = 0
    ARROW_IS_RUNNING = 1
    ARROW_IS_FINISHED = 2


def get_winner_sector(angle, used_questions):
    sector = vlk.get_sector(angle)
    while sector in used_questions:
        logger.debug('Sector %d is already used, trying next', sector)
        sector += 1
        if sector == 14:
            sector = 1
    logger.info('Sector %d is a winner', sector)
    return sector


class GameRound(object):
    MAX_VELOCITY = 5.
    MIN_SECONDS = 34
    MAX_SECONDS = 42

    def __init__(self, config, volchok):
        self._config = config
        self._volchok = volchok
        self._state = RoundState.INIT
        self._arrow_angle = 0.
        self._seconds = random.uniform(self.MIN_SECONDS, self.MAX_SECONDS)
        self._velocity = (self._seconds / FRAME_UPDATE) * VELOCITY_DELTA

        self._winner_sector = None

    def can_start_arrow(self):
        if self._state != RoundState.INIT:
            logger.critical('In a wrong state')
            raise RuntimeError('Wrong state: false transition to CAN_START_ARROW')
        self._state = RoundState.CAN_START_ARROW

    def tick(self, _):
        if self._state in [RoundState.INIT, RoundState.ARROW_IS_FINISHED]:
            return
        if self._state == RoundState.CAN_START_ARROW:
            logger.info('Staring arrow for %.2f seconds', self._seconds)
            self._state = RoundState.ARROW_IS_RUNNING

        self._arrow_angle = (self._arrow_angle + min(self.MAX_VELOCITY, self._velocity)) % 360
        self._volchok.update_arrow(self._arrow_angle)

        self._velocity = max(0., self._velocity - VELOCITY_DELTA)
        if self._velocity == 0.:
            self._winner_sector = get_winner_sector(self._arrow_angle, self._config.used_questions)
            self._state = RoundState.ARROW_IS_FINISHED



def main():
    win = pyglet.window.Window(width=common.WIDTH, height=common.HEIGHT)
    config = common.load_config('cfg.json')
    volchok = vlk.Volchok(config)
    game_round = GameRound(config, volchok)


    @win.event
    def on_draw():
        volchok.draw()

    @win.event
    def on_key_press(symbol, modifiers):
        if symbol == key.SPACE:
            game_round.can_start_arrow()

    pyglet.clock.schedule_interval(game_round.tick, FRAME_UPDATE)
    pyglet.app.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
