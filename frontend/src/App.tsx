import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";

import { TopBar } from "./components/TopBar";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { HomePage } from "./pages/HomePage";
import { SettingsPage } from "./pages/SettingsPage";
import { DeckShell } from "./widgets/DeckShell";

// Add entries here as new routes are introduced.
const ROUTE_TITLES: Record<string, string> = {
  "/settings": "Settings",
};

function AppInner() {
  const deck = useDeckEvents();
  const location = useLocation();
  const title = ROUTE_TITLES[location.pathname];

  return (
    <DeckShell>
      <TopBar title={title} />
      <Routes>
        <Route path="/" element={<HomePage deck={deck} />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </DeckShell>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
