import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout    from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Upload    from "@/pages/Upload";
import Truth     from "@/pages/Truth";
import Configure from "@/pages/Configure";
import Run       from "@/pages/Run";
import Results   from "@/pages/Results";
import Versions  from "@/pages/Versions";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index          element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload"    element={<Upload />} />
          <Route path="truth"     element={<Truth />} />
          <Route path="configure" element={<Configure />} />
          <Route path="run"       element={<Run />} />
          <Route path="results"   element={<Results />} />
          <Route path="versions"  element={<Versions />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
