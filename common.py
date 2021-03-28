from dataclasses import dataclass, field
from typing import Set, Optional
import json

WIDTH, HEIGHT = 800, 800

@dataclass
class GameConfig:
    used_questions: Set[int] = field(default_factory=set)
    blitz_idx: Optional[int] = None
    superblitz_idx: Optional[int] = None


def load_config(path):
    with open(path) as fin:
        data = json.load(fin)
    return GameConfig(
        used_questions=set(data['used']),
        blitz_idx=data['blitz'],
        superblitz_idx=data['superblitz']
    )
