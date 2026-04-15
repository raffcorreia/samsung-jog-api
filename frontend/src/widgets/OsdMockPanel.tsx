import { useState } from "react";
import styles from "./OsdMockPanel.module.css";

// Samsung CJ791 OSD — main menu categories (horizontal tabs)
const MENU_TABS = [
  { id: "eye-care", label: "Eye Care" },
  { id: "picture", label: "Picture" },
  { id: "color", label: "Color" },
  { id: "display", label: "Display" },
  { id: "pbp", label: "PBP/PiP" },
  { id: "system", label: "System" },
  { id: "info", label: "Information" },
] as const;

type TabId = (typeof MENU_TABS)[number]["id"];

// Sub-items per tab — realistic values for CJ791
const TAB_ITEMS: Record<TabId, { label: string; value: string }[]> = {
  "eye-care": [
    { label: "Eye Saver Mode", value: "Off" },
    { label: "Flicker Free", value: "On" },
    { label: "Smart ECO Saving", value: "Off" },
  ],
  picture: [
    { label: "Picture Mode", value: "Custom" },
    { label: "Brightness", value: "100" },
    { label: "Contrast", value: "75" },
    { label: "Sharpness", value: "60" },
    { label: "Game Mode", value: "Off" },
    { label: "Black Level", value: "Low" },
  ],
  color: [
    { label: "Red", value: "50" },
    { label: "Green", value: "50" },
    { label: "Blue", value: "50" },
    { label: "Color Tone", value: "Normal" },
    { label: "Gamma", value: "Mode 1" },
  ],
  display: [
    { label: "Resolution", value: "3440×1440" },
    { label: "Wide Screen", value: "21:9" },
    { label: "Screen Adj", value: "—" },
    { label: "DisplayPort Ver.", value: "1.2" },
  ],
  pbp: [
    { label: "Mode", value: "Off" },
    { label: "Picture Size", value: "—" },
    { label: "Source", value: "—" },
    { label: "Sound", value: "—" },
  ],
  system: [
    { label: "Language", value: "English" },
    { label: "Menu Transparency", value: "25" },
    { label: "Power LED On", value: "On" },
    { label: "Eco Savings Timer", value: "Off" },
    { label: "Reset All", value: "—" },
  ],
  info: [
    { label: "Model", value: "C49J79" },
    { label: "Resolution", value: "3440×1440" },
    { label: "Optimal Resolution", value: "3440×1440@60Hz" },
    { label: "Input", value: "DisplayPort 1" },
    { label: "Version", value: "M-S1AG-0" },
  ],
};

/**
 * Mock representation of the Samsung CJ791 OSD.
 *
 * Phase 13: static interactive stub — user can click tabs to explore.
 * Phase 15: this component will be driven by real bus observation events.
 */
export function OsdMockPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("eye-care");
  const [selectedItem, setSelectedItem] = useState(0);
  const items = TAB_ITEMS[activeTab];

  return (
    <div className={styles.osd} data-testid="osd-mock-panel">
      {/* Brand header */}
      <div className={styles.brand}>
        <span className={styles.brandName}>SAMSUNG</span>
        <span className={styles.modelName}>CJ791</span>
      </div>

      {/* Horizontal tab bar */}
      <nav className={styles.tabBar} role="tablist" aria-label="OSD Menu">
        {MENU_TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            type="button"
            aria-selected={tab.id === activeTab}
            className={`${styles.tab} ${tab.id === activeTab ? styles.tabActive : ""}`}
            onClick={() => {
              setActiveTab(tab.id);
              setSelectedItem(0);
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Sub-item list */}
      <ul className={styles.itemList} role="tabpanel">
        {items.map((item, i) => (
          <li
            key={item.label}
            className={`${styles.item} ${i === selectedItem ? styles.itemSelected : ""}`}
            onPointerDown={() => setSelectedItem(i)}
          >
            <span className={styles.itemLabel}>{item.label}</span>
            <span className={styles.itemValue}>{item.value}</span>
          </li>
        ))}
      </ul>

      {/* Bottom controls hint */}
      <div className={styles.controls}>
        <span>JOG</span>
        <span className={styles.controlSep}>Navigate</span>
        <span>ENTER</span>
        <span className={styles.controlSep}>Select</span>
        <span>LEFT</span>
        <span className={styles.controlSep}>Back</span>
      </div>
    </div>
  );
}
