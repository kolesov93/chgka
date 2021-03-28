import pyglet
from common import GameConfig, WIDTH, HEIGHT
import math
import logging


logger = logging.getLogger('volchok')
logger.setLevel(logging.DEBUG)

SCALE = WIDTH / 2000.
LETTER_SCALE = 0.3
TABLE_RADIUS = 330


def get_sector(angle):
    angle_step = 360 / 13.
    if angle < angle_step / 2. or angle_step > 360. - angle_step:
        return 13
    cur = angle_step / 2
    for i in range(12):
        if angle >= cur and angle <= cur + angle_step:
            return i + 1
        cur += angle_step
    return 12


class Groups:
    TABLE = 0
    ARROW = 1
    VOLCHOK = 2
    LETTER = 3


def _load_letter_image(path):
    the_image = pyglet.image.load(path)
    the_image.anchor_x = the_image.width // 2
    the_image.anchor_y = the_image.height // 2
    return the_image


class Images:
    LETTER = _load_letter_image('letter.png')
    BLITZ_LETTER = _load_letter_image('blitz.png')
    SUPERBLITZ_LETTER = _load_letter_image('superblitz.png')
    TABLE_WITH_13 = pyglet.image.load('table.png')
    TABLE_WITHOUT_13 = pyglet.image.load('table_all_arrows.png')
    ARROW = pyglet.image.load('red_arrow.png')
    VOLCHOK = pyglet.image.load('volchok.png')


class Volchok(object):

    def __init__(self, game_config: GameConfig, win):
        self._win = win
        self._game_config = game_config

        self._batch = pyglet.graphics.Batch()
        self._groups = [
            pyglet.graphics.OrderedGroup(i)
            for i in range(4)
        ]

        self._nogc = []

        self._prepare_table_group()
        self._prepare_letter_group()
        self._arrow = self._prepare_and_return_arrow()
        self._prepare_volchok_group()

        self._table_sprite = None

    def set_table_sprite(self, sprite):
        self._table_sprite = sprite

    def update_arrow(self, angle):
        self._arrow.update(rotation=angle)

    def draw(self):
        if self._table_sprite:
            self._win.clear()
            self._table_sprite.draw()
            return
        self._batch.draw()

    def _prepare_table_group(self):
        if 13 not in self._game_config.used_questions:
            table_image = Images.TABLE_WITH_13
        else:
            table_image = Images.TABLE_WITHOUT_13
        table = pyglet.sprite.Sprite(
            table_image,
            x=0, y=0,
            batch=self._batch,
            group=self._groups[Groups.TABLE]
        )
        table.update(scale=SCALE)
        self._nogc.append(table)

    def _prepare_letter_group(self):
        for i in range(12):
            if i + 1 in self._game_config.used_questions:
                logger.debug('%d: used', i + 1)
                continue

            if i == self._game_config.superblitz_idx:
                the_image = Images.SUPERBLITZ_LETTER
                logger.debug('%d: superblitz', i + 1)
            elif i == self._game_config.blitz_idx:
                the_image = Images.BLITZ_LETTER
                logger.debug('%d: blitz', i + 1)
            else:
                the_image = Images.LETTER
                logger.debug('%d: usual', i + 1)

            letter = pyglet.sprite.Sprite(
                the_image,
                x=0, y=0,
                batch=self._batch,
                group=self._groups[Groups.LETTER]
            )
            letter_angle = 1.5 * math.pi - (2 * math.pi) / 13 * (i + 1)
            if letter_angle < 0.:
                letter_angle += 2 * math.pi
            letter.update(
                scale=LETTER_SCALE,
                x=WIDTH / 2 + math.cos(letter_angle) * TABLE_RADIUS,
                y=HEIGHT / 2 + math.sin(letter_angle) * TABLE_RADIUS,
                rotation=-letter_angle * 180. / math.pi + 90.
            )
            self._nogc.append(letter)

    def _prepare_and_return_arrow(self):
        arrow = pyglet.sprite.Sprite(
            Images.ARROW,
            x=0., y=0.,
            subpixel=True,
            batch=self._batch,
            group=self._groups[Groups.ARROW]
        )
        arrow.image.anchor_x = arrow.image.width / 2
        arrow.image.anchor_y = arrow.image.height
        arrow.update(
            scale=SCALE,
            x=WIDTH/2,
            y=HEIGHT/2
        )
        return arrow

    def _prepare_volchok_group(self):
        volchok = pyglet.sprite.Sprite(
            Images.VOLCHOK,
            x=WIDTH/2 - Images.VOLCHOK.width * SCALE / 2,
            y=WIDTH/2 - Images.VOLCHOK.height * SCALE / 2,
            subpixel=True,
            batch=self._batch,
            group=self._groups[Groups.VOLCHOK]
        )
        volchok.update(scale=SCALE)
        self._nogc.append(volchok)



