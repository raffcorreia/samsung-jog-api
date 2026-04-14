import { describe, expect, it } from "vitest";

import { bumpHeldCount, restDownUndoesPreRestPeer } from "./deckHoldPeerSync";

describe("deckHoldPeerSync", () => {
  it("bumpHeldCount clamps at zero", () => {
    expect(bumpHeldCount({}, "up", 1)).toEqual({ up: 1 });
    expect(bumpHeldCount({ up: 1 }, "up", -1)).toEqual({});
    expect(bumpHeldCount({}, "up", -1)).toEqual({});
  });

  it("restDownUndoesPreRestPeer removes phantom peer bump when WS won the race", () => {
    const preRest = new Map<string, "up">([["tok-a", "up"]]);
    const { peer, preRest: nextPre } = restDownUndoesPreRestPeer({ up: 1 }, preRest, "tok-a", "up");
    expect(peer).toEqual({});
    expect(nextPre.size).toBe(0);
  });
});
