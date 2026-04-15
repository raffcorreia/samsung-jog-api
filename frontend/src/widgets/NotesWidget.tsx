import { DECK_WIDGETS } from "./deckWidgets";
import styles from "./NotesWidget.module.css";

interface Note {
  id: number;
  title: string;
  body: string;
}

// Mock notes that look like real development notes for this project.
const MOCK_NOTES: Note[] = [
  {
    id: 1,
    title: "PiP sequence",
    body: "Center → wait LED → Left × 3 → Center",
  },
  {
    id: 2,
    title: "Input cycling",
    body: "TB → HDMI → DP → TB — ~3 presses from closed",
  },
  {
    id: 3,
    title: "OSD timeout",
    body: "Closes after ~8 s idle — use wait_ddc for sync",
  },
  {
    id: 4,
    title: "LED blink",
    body: "Blue blink on input change, solid = active, off = standby",
  },
];

export function NotesWidget() {
  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.notes}>
      <h2 className={styles.header}>Notes</h2>
      <ul className={styles.list}>
        {MOCK_NOTES.map((note) => (
          <li key={note.id} className={styles.note}>
            <span className={styles.noteTitle}>{note.title}</span>
            <span className={styles.noteBody}>{note.body}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
