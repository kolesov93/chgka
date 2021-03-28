import volchok as vlk
import common
import os
import pyglet
from pyglet.window import key
import logging
import random
import subprocess as sp

logger = logging.getLogger('game')
logger.setLevel(logging.DEBUG)

FRAME_UPDATE = 0.02
VELOCITY_DELTA = 0.01

class AppState:
    INTRO = 0
    VOLCHOK = 1


state = AppState.INTRO

class RoundState:
    INIT = -1
    CAN_START_ARROW = 0
    ARROW_IS_RUNNING = 1
    ARROW_IS_FINISHED = 2
    TABLE = 3


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

        self._audio_process = None
        self._table_sprite = None

    def can_start_arrow(self):
        if self._state != RoundState.INIT:
            logger.warning('Unexpected call to start an arrow. Ignoring')
            return
        self._state = RoundState.CAN_START_ARROW

    def yes(self):
        if self._audio_process:
            self._audio_process.terminate()
        fname = random.choice(['sound/yes1.mp3', 'sound/yes2.mp3'])
        self._audio_process = sp.Popen(['vlc', '-I', 'dummy', fname])

    def no(self):
        if self._audio_process:
            self._audio_process.terminate()
        fname = random.choice(['sound/no1.mp3', 'sound/no2.mp3'])
        self._audio_process = sp.Popen(['vlc', '-I', 'dummy', fname])

    def _sig(self, path):
        try:
            sp.call(['vlc', '--play-and-exit', '-I', 'dummy', path], timeout=1.)
        except sp.TimeoutExpired:
            pass

    def sig1(self):
        self._sig('sound/sig2.mp3')

    def sig2(self):
        self._sig('sound/sig3.mp3')

    def show_table(self, a, b):
        fname = 'table/{}{}.png'.format(a, b)
        the_image = pyglet.image.load(fname)
        the_scale = min(
            common.WIDTH / the_image.width,
            common.HEIGHT / the_image.height,
            1.
        )
        sprite = pyglet.sprite.Sprite(
            the_image,
            x=0,
            y=0,
        )
        sprite.update(
            x=(common.WIDTH - the_image.width * the_scale) / 2.,
            y=(common.HEIGHT - the_image.height * the_scale) / 2.,
            scale=the_scale
        )
        self._table_sprite = sprite
        self._volchok.set_table_sprite(sprite)
        self._state = RoundState.TABLE

    def tick(self, _):
        if self._state in [RoundState.INIT, RoundState.ARROW_IS_FINISHED, RoundState.TABLE]:
            return
        if self._state == RoundState.CAN_START_ARROW:
            logger.info('Staring arrow for %.2f seconds', self._seconds)
            self._state = RoundState.ARROW_IS_RUNNING
            self._audio_process = sp.Popen(['vlc', '-I', 'dummy', 'sound/volchok.mp3'])


        self._arrow_angle = (self._arrow_angle + min(self.MAX_VELOCITY, self._velocity)) % 360
        self._volchok.update_arrow(self._arrow_angle)

        self._velocity = max(0., self._velocity - VELOCITY_DELTA)
        if self._velocity == 0.:
            self._winner_sector = get_winner_sector(self._arrow_angle, self._config.used_questions)
            self._state = RoundState.ARROW_IS_FINISHED
            if self._audio_process:
                self._audio_process.terminate()
            self._config.used_questions.add(self._winner_sector)
            common.dump_config('cfg.json', self._config)



class Intro(object):

    def __init__(self, win):
        self._win = win
        self._audio_process = None

        self._frames = []
        for fname in self._load_frames():
            the_image = pyglet.image.load(fname)
            the_scale = min(
                common.WIDTH / the_image.width,
                common.HEIGHT / the_image.height,
                1.
            )
            self._frames.append(
                pyglet.sprite.Sprite(
                    the_image,
                    x=0,
                    y=0,
                )
            )
            self._frames[-1].update(
                x=(common.WIDTH - the_image.width * the_scale) / 2.,
                y=(common.HEIGHT - the_image.height * the_scale) / 2.,
                scale=the_scale
            )
        self._frame_idx = -1

    def _load_frames(self):
        result = []
        for fname in os.listdir('intro'):
            if any(fname.endswith(prefix) for prefix in ['.jpg', '.JPG', '.png']):
                logger.debug('Found frame %s', fname)
                result.append(os.path.join('intro', fname))
        logger.info('Found %d frames for intro', len(result))
        result.sort()
        return result

    def next_frame(self):
        self._frame_idx += 1
        if self._frame_idx == 0:
            self._audio_process = sp.Popen(['vlc', '-I', 'dummy', 'sound/meeting.mp3'])
        if self._frame_idx >= len(self._frames):
            if self._audio_process:
                self._audio_process.terminate()

    def draw(self):
        if self._frame_idx < 0 or self._frame_idx >= len(self._frames):
            return

        self._win.clear()
        self._frames[self._frame_idx].draw()

    def tick(self, _):
        pass


def main():
    win = pyglet.window.Window(width=common.WIDTH, height=common.HEIGHT)
    config = common.load_config('cfg.json')
    volchok = vlk.Volchok(config, win)
    game_round = GameRound(config, volchok)
    intro = Intro(win)


    @win.event
    def on_draw():
        if state == AppState.INTRO:
            intro.draw()
        elif state == AppState.VOLCHOK:
            volchok.draw()
        else:
            raise ValueError('Unknown state {}'.format(state))

    @win.event
    def on_key_press(symbol, modifiers):
        global state
        if state == AppState.INTRO:
            if symbol == key.SPACE:
                intro.next_frame()
            elif symbol == key.RETURN:
                state = AppState.VOLCHOK
        elif state == AppState.VOLCHOK:
            if symbol == key.SPACE:
                game_round.can_start_arrow()
            if modifiers & key.MOD_CTRL:
                if symbol == key.N:
                    game_round.no()
                    config.tv_score += 1
                    game_round.show_table(config.znatoki_score, config.tv_score)
                    common.dump_config('cfg.json', config)
                elif symbol == key.Y:
                    game_round.yes()
                    config.znatoki_score += 1
                    game_round.show_table(config.znatoki_score, config.tv_score)
                    common.dump_config('cfg.json', config)
                elif symbol == key.S:
                    game_round.sig1()
                elif symbol == key.T:
                    game_round.sig2()
        else:
            raise ValueError('Unknown state {}'.format(state))

    pyglet.clock.schedule_interval(game_round.tick, FRAME_UPDATE)
    pyglet.app.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
