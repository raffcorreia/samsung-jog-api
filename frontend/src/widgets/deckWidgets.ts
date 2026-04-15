/**
 * Stable widget ids for layout persistence / show-hide (future).
 * Components set `data-widget={DECK_WIDGETS.jog}` on their root.
 */
export const DECK_WIDGETS = {
  jog: "deck-jog",
  log: "deck-log",
  calendar: "deck-calendar",
  notes: "deck-notes",
  settings: "deck-settings",
} as const;

export type DeckWidgetId = (typeof DECK_WIDGETS)[keyof typeof DECK_WIDGETS];
