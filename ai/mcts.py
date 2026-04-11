import math
import random
from ai.evaluation import evaluate
class _MCTSNode:
    __slots__ = ("state","action","parent","children","wins","visits","untried")
    def __init__(self, state, action=None, parent=None):
        self.state    = state
        self.action   = action
        self.parent   = parent
        self.children = []
        self.wins     = 0.0
        self.visits   = 0
        acts          = state.get_legal_actions()
        self.untried  = [a for a in acts if a is not None] or [None]

    def uct(self):
        logn = math.log(self.visits+1)
        return max(self.children,
                   key=lambda c: c.wins/max(c.visits,1)+1.41*math.sqrt(logn/max(c.visits,1)))

    def expand(self):
        a = self.untried.pop()
        child = _MCTSNode(self.state.apply(a), a, self)
        self.children.append(child); return child

    def rollout(self, fp, steps=18):
        s = self.state._clone()
        for _ in range(steps):
            if s.is_terminal(): break
            s = s.apply(random.choice(s.get_legal_actions()))
        return evaluate(s, fp)

    def backprop(self, v):
        self.visits += 1; self.wins += v
        if self.parent: self.parent.backprop(v)

class MCTSAI:
    def __init__(self, iters=600): self.iters = iters
    def choose(self, state):
        root = _MCTSNode(state); fp = state.current_player
        for _ in range(self.iters):
            node = root
            while not node.untried and node.children: node = node.uct()
            if node.untried: node = node.expand()
            node.backprop(node.rollout(fp))
        if not root.children: return None
        return max(root.children, key=lambda c: c.visits).action
