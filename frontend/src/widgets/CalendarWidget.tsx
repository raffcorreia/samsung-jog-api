import { DECK_WIDGETS } from "./deckWidgets";
import styles from "./CalendarWidget.module.css";

// April 2026: starts on Wednesday (index 2 in Mon-based week).
const MONTH_LABEL = "April 2026";
const TODAY = 15;
const FIRST_DAY_OFFSET = 2; // 0 = Mon, 2 = Wed
const DAYS_IN_MONTH = 30;
const DAY_LABELS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

interface MockEvent {
  day: number;
  time: string;
  label: string;
}

const MOCK_EVENTS: MockEvent[] = [
  { day: 15, time: "09:00", label: "Deck bring-up" },
  { day: 17, time: "14:30", label: "Hardware review" },
  { day: 22, time: "10:00", label: "OSD investigation" },
  { day: 28, time: "16:00", label: "Phase 14 planning" },
];

const TODAY_EVENTS = MOCK_EVENTS.filter((e) => e.day === TODAY);

export function CalendarWidget() {
  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.calendar}>
      <h2 className={styles.header}>{MONTH_LABEL}</h2>

      <div className={styles.grid} role="grid" aria-label={MONTH_LABEL}>
        {DAY_LABELS.map((d) => (
          <span key={d} className={styles.dayLabel} role="columnheader">
            {d}
          </span>
        ))}
        {Array.from({ length: FIRST_DAY_OFFSET }, (_, i) => (
          <span key={`pad-${i}`} aria-hidden="true" />
        ))}
        {Array.from({ length: DAYS_IN_MONTH }, (_, i) => {
          const day = i + 1;
          const hasEvent = MOCK_EVENTS.some((e) => e.day === day);
          return (
            <span
              key={day}
              className={`${styles.day} ${day === TODAY ? styles.today : ""} ${hasEvent ? styles.hasEvent : ""}`}
              role="gridcell"
              aria-current={day === TODAY ? "date" : undefined}
            >
              {day}
            </span>
          );
        })}
      </div>

      {TODAY_EVENTS.length > 0 && (
        <ul className={styles.eventList} aria-label="Today's events">
          {TODAY_EVENTS.map((ev) => (
            <li key={`${ev.day}-${ev.time}`} className={styles.event}>
              <span className={styles.eventTime}>{ev.time}</span>
              <span className={styles.eventLabel}>{ev.label}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
