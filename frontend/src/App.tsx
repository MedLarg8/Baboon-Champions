import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { FriendsPage } from "./pages/FriendsPage";
import { GameDetailPage } from "./pages/GameDetailPage";
import { GameHistoryPage } from "./pages/GameHistoryPage";
import { NewGamePage } from "./pages/NewGamePage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="friends" element={<FriendsPage />} />
        <Route path="games" element={<GameHistoryPage />} />
        <Route path="games/new" element={<NewGamePage />} />
        <Route path="games/:id" element={<GameDetailPage />} />
        <Route path="matches" element={<Navigate to="/games" replace />} />
        <Route path="matches/:id" element={<Navigate to="/games" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
