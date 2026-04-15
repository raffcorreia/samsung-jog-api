import styles from "./VersionBadge.module.css";

interface Props {
  version: string;
}

/** Floating version badge — fixed top-left, sourced from status.version. */
export function VersionBadge({ version }: Props) {
  return (
    <div className={styles.badge} data-testid="version-badge">
      {version}
    </div>
  );
}
