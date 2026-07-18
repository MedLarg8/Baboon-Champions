import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { FriendsPage } from "./pages/FriendsPage";
import { MatchDetailPage } from "./pages/MatchDetailPage";
import { MatchHistoryPage } from "./pages/MatchHistoryPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="friends" element={<FriendsPage />} />
        <Route path="matches" element={<MatchHistoryPage />} />
        <Route path="matches/:id" element={<MatchDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
