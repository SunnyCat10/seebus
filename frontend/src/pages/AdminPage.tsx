import {AdminGate} from "../components/admin/AdminGate.tsx";
import {useState} from "react";
import {AdminDashboard} from "../components/admin/AdminDashboard.tsx";
import {PageLayout} from "../components/layout/PageLayout.tsx";
import {IconButton} from "@chakra-ui/react";
import {LuArrowLeft} from "react-icons/lu";
import {Link as RouterLink} from "react-router-dom";

export function AdminPage() {
    const [adminToken, setAdminToken] = useState<string | null>(
        () => sessionStorage.getItem("seebus-admin-token"),
    );

    return (
        <PageLayout
            headerAction={
                <IconButton
                    asChild
                    aria-label="Back to public view"
                    variant="ghost"
                >
                    <RouterLink to="/">
                        <LuArrowLeft />
                    </RouterLink>
                </IconButton>
            }
        >
            {!adminToken ? (
                <AdminGate
                    onUnlock={setAdminToken}
                />
            ) : (
                <AdminDashboard
                    adminToken={adminToken}
                />
            )}
        </PageLayout>
    );
}