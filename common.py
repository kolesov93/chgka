from dataclasses import dataclass, field
from typing import Set, Optional
import json

WIDTH, HEIGHT = 800, 800

@dataclass
class GameConfig:
    used_questions: Set[int] = field(default_factory=set)
    blitz_idx: Optional[int] = None
    superblitz_idx: Optional[int] = None
    znatoki_score: int = 0
    tv_score: int = 0


def load_config(path):
    with open(path) as fin:
        data = json.load(fin)
    return GameConfig(
        used_questions=set(data['used']),
        blitz_idx=data['blitz'],
        superblitz_idx=data['superblitz'],
        znatoki_score=data['znatoki'],
        tv_score=data['tv']
    )

def dump_config(path, cfg):
    with open(path, 'w') as fout:
        json.dump(
            {
                'used': list(cfg.used_questions),
                'blitz': cfg.blitz_idx,
                'superblitz': cfg.superblitz_idx,
                'znatoki': cfg.znatoki_score,
                'tv': cfg.tv_score
            },
            fout
        )
