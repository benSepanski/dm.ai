import { Navigate, Route, Routes } from "react-router-dom";
import CharacterCreationWizard from "./components/CharacterCreation/CharacterCreationWizard";
import DMDashboard from "./components/DMDashboard/DMDashboard";
import NewSessionForm from "./components/DMDashboard/NewSessionForm";
import { useGameStore } from "./store/gameStore";

// "/" resumes the persisted session if one exists; otherwise shows the
// new-session form. "/session/:sessionId" is the shareable session URL —
// other devices on the LAN join the game by opening it.
function Home() {
  const sessionId = useGameStore((s) => s.sessionId);
  if (sessionId) {
    return <Navigate to={`/session/${sessionId}`} replace />;
  }
  return (
    <div
      style={{
        height: "100vh",
        background: "#0d0d1a",
        color: "#fff",
        fontFamily: "sans-serif",
      }}
    >
      <NewSessionForm />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session/:sessionId" element={<DMDashboard />} />
      <Route path="/world/:worldId/create-character" element={<CharacterCreationWizard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
