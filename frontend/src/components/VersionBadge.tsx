import styles from "./VersionBadge.module.css";

interface Props {
  version: string;
}

/** Compact version badge shown beside the top-bar clock. */
export function VersionBadge({ version }: Props) {
  return (
    <div className={styles.badge} data-testid="version-badge">
      {version}
    </div>
  );
}
