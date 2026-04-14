import type { JogAction } from "../types";

/** Mutable refs used by useDeckEvents — kept pure here for tests. */
export function bumpHeldCount(
  prev: Record<JogAction, number>,
  action: JogAction,
  delta: 1 | -1,
): Record<JogAction, number> {
  const n = Math.max(0, (prev[action] ?? 0) + delta);
  const next: Record<JogAction, number> = { ...prev };
  if (n === 0) {
    delete next[action];
  } else {
    next[action] = n;
  }
  return next;
}

/**
 * WS arrived before REST — peer was incremented; REST later confirms same token and undoes one peer bump.
 */
export function restDownUndoesPreRestPeer(
  peer: Record<JogAction, number>,
  preRest: Map<string, JogAction>,
  token: string,
  action: JogAction,
): { peer: Record<JogAction, number>; preRest: Map<string, JogAction> } {
  const pre = preRest.get(token);
  const nextPre = new Map(preRest);
  nextPre.delete(token);
  if (pre !== undefined && pre === action) {
    return { peer: bumpHeldCount(peer, action, -1), preRest: nextPre };
  }
  return { peer, preRest: nextPre };
}
