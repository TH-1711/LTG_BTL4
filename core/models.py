from core.constants import UNIT_STATS
from core.constants import TILE
class Unit:
    _next_id = 1

    def __init__(self, owner, utype, x, y, uid=None):
        self.id      = uid if uid is not None else Unit._alloc()
        self.owner   = owner
        self.type    = utype
        self.x       = x
        self.y       = y
        self.hp      = UNIT_STATS[utype]["hp"]
        self.max_hp  = self.hp

    @staticmethod
    def _alloc():
        uid = Unit._next_id; Unit._next_id += 1; return uid

    @property
    def alive(self): return self.hp > 0

    def clone(self):
        u = Unit.__new__(Unit); u.__dict__.update(self.__dict__); return u

    def center_px(self):
        return self.x * TILE + TILE // 2, self.y * TILE + TILE // 2

    def __repr__(self):
        return f"<{UNIT_STATS[self.type]['label']} P{self.owner} ({self.x},{self.y}) hp={self.hp}>"


class MoveAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty

class AttackAction:
    def __init__(self, unit_id, tx, ty):
        self.unit_id = unit_id
        self.tx, self.ty = tx, ty