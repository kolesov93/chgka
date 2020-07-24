import math
import pyglet
import numpy as np
import math
import random
import json
from pyglet.window import key

MIN_SECONDS, MAX_SECONDS = 34, 42
WIDTH, HEIGHT = 800, 800
SCALE = WIDTH / 2000.
LETTER_SCALE = 0.3
TABLE_RADIUS = 330
FRAME_UPDATE = 0.02
VELOCITY_DELTA = 0.01
win = pyglet.window.Window(width=WIDTH, height=HEIGHT)

played = json.load(open('played.json'))
assert len(played) == len(set(played))
assert len(played) < 13

sound = pyglet.media.load('sound/volchok.mp3', streaming=False)
player = pyglet.media.Player()
player.queue(sound)

batch = pyglet.graphics.Batch()
table_group = pyglet.graphics.OrderedGroup(0)
arrow_group = pyglet.graphics.OrderedGroup(1)
volchok_group = pyglet.graphics.OrderedGroup(2)
letter_group = pyglet.graphics.OrderedGroup(3)

if 13 not in played:
    table_image = pyglet.image.load('table.png')
else:
    table_image = pyglet.image.load('table_all_arrows.png')
table = pyglet.sprite.Sprite(table_image, x=0, y=0, batch=batch, group=table_group)
table.update(scale=SCALE)

letter_image = pyglet.image.load('letter.png')
letter_image.anchor_x = letter_image.width // 2
letter_image.anchor_y = letter_image.height // 2
letters = []
for i in range(12):
    if i + 1 in played:
        continue
    letter = pyglet.sprite.Sprite(letter_image, x=0, y=0, batch=batch, group=letter_group)
    letter_angle = 1.5 * math.pi - (2 * math.pi) / 13 * (i + 1)
    if letter_angle < 0.:
        letter_angle += 2 * math.pi
    letter.update(
        scale=LETTER_SCALE,
        x=WIDTH / 2 + math.cos(letter_angle) * TABLE_RADIUS,
        y=HEIGHT / 2 + math.sin(letter_angle) * TABLE_RADIUS,
        rotation=-letter_angle * 180. / math.pi + 90.
    )
    letters.append(letter)

arrow_image = pyglet.image.load('red_arrow.png')
arrow = pyglet.sprite.Sprite(
    arrow_image,
    x=0., y=0.,
    subpixel=True,
    batch=batch,
    group=arrow_group
)
arrow.image.anchor_x = arrow.image.width / 2
arrow.image.anchor_y = arrow.image.height
arrow.update(
    scale=SCALE,
    x=WIDTH/2,
    y=HEIGHT/2
)

volchok_image = pyglet.image.load('volchok.png')
volchok = pyglet.sprite.Sprite(
    volchok_image,
    x=WIDTH/2 - volchok_image.width * SCALE / 2,
    y=WIDTH/2 - volchok_image.height * SCALE / 2,
    subpixel=True,
    batch=batch,
    group=volchok_group
)
volchok.update(scale=SCALE)

def _get_sector(angle):
    angle_step = 360 / 13.
    if angle < angle_step / 2. or angle_step > 360. - angle_step:
        return 13
    cur = angle_step / 2
    for i in range(12):
        if angle >= cur and angle <= cur + angle_step:
            return i + 1
        cur += angle_step
    return 12

angle = 0.
seconds = random.uniform(MIN_SECONDS, MAX_SECONDS)
print('Will play for {} seconds'.format(seconds))
velocity = (seconds / FRAME_UPDATE) * VELOCITY_DELTA
started = False
can_start = False
finished = False
def update_frame(dt):
    global angle, velocity, started, can_start, finished
    if not can_start or finished:
        return
    if not started:
        player.play()
        started = True

    MAX_VELOCITY = 5.

    angle = (angle + min(MAX_VELOCITY, velocity)) % 360
    arrow.update(rotation=angle)

    velocity = max(0., velocity - VELOCITY_DELTA)
    if velocity == 0.:
        player.pause()
        sector = _get_sector(angle)
        while sector in played:
            print('Sector {} already played, trying next'.format(sector))
            sector += 1
            if sector == 14:
                sector = 1
        print('Done', sector)
        played.append(sector)
        with open('played.json', 'w') as fout:
            json.dump(played, fout)
        finished = True


@win.event
def on_draw():
    batch.draw()


@win.event
def on_key_press(symbol, modifiers):
    global can_start
    if symbol == key.SPACE:
        can_start = True


pyglet.clock.schedule_interval(update_frame, FRAME_UPDATE)
pyglet.app.run()
