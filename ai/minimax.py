import math
import random
from ai.evaluation import evaluate

def minimax(state, depth, alpha, beta, fp):
    if depth==0 or state.is_terminal():
        return evaluate(state, fp), None
    actions = state.get_legal_actions()
    random.shuffle(actions)
    best_a = actions[0]
    if state.current_player == fp:
        best = -math.inf
        for a in actions[:14]:
            val, _ = minimax(state.apply(a), depth-1, alpha, beta, fp)
            if val > best: best, best_a = val, a
            alpha = max(alpha, best)
            if beta <= alpha: break
        return best, best_a
    else:
        best = math.inf
        for a in actions[:14]:
            val, _ = minimax(state.apply(a), depth-1, alpha, beta, fp)
            if val < best: best, best_a = val, a
            beta = min(beta, best)
            if beta <= alpha: break
        return best, best_a

class MinimaxAI:
    def choose(self, state):
        _, a = minimax(state, 2, -math.inf, math.inf, state.current_player)
        return a