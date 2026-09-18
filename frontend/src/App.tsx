import {
    BrowserRouter,
    Navigate,
    Route,
    Routes,
} from "react-router-dom";

import { SchedulePage } from "./pages/SchedulePage";
import { AdminPage } from "./pages/AdminPage";

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<SchedulePage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;