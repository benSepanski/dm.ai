import { Route, Routes } from "react-router-dom";
import DMDashboard from "./components/DMDashboard/DMDashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DMDashboard />} />
    </Routes>
  );
}
