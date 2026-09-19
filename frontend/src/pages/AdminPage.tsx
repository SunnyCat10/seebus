import {AdminGate} from "../components/admin/AdminGate.tsx";
import {useState} from "react";
import {AdminDashboard} from "../components/admin/AdminDashboard.tsx";

export function AdminPage() {
    const [adminToken, setAdminToken] = useState<string | null>(
        () => sessionStorage.getItem("seebus-admin-token"),
    );

    if (!adminToken) {
        return (
            <AdminGate onUnlock={setAdminToken}/>
        );
    }

    return (
        <AdminDashboard adminToken={adminToken}/>
    );
}