from core.constants import PLAYER_HUMAN, PLAYER_AI

def evaluate(state, for_player):
    if state.is_terminal():
        w = state.winner()
        if w == for_player: return 10000
        if w is not None: return -10000
        return 0

    opp = 1 - for_player

    my_hp  = sum(u.hp for u in state.units if u.owner == for_player)
    opp_hp = sum(u.hp for u in state.units if u.owner == opp)

    my_n  = sum(1 for u in state.units if u.owner == for_player)
    opp_n = sum(1 for u in state.units if u.owner == opp)

    score = (my_hp - opp_hp)*2 + (my_n - opp_n)*10
    return score