import {AdminGate} from "../components/admin/AdminGate.tsx";
import {useState} from "react";
import {AdminDashboard} from "../components/admin/AdminDashboard.tsx";
import {PageLayout} from "../components/layout/PageLayout.tsx";
import {Button} from "@chakra-ui/react";
import {LuArrowLeft} from "react-icons/lu";
import {Link as RouterLink} from "react-router-dom";

export function AdminPage() {
    const [adminToken, setAdminToken] = useState<string | null>(
        () => sessionStorage.getItem("seebus-admin-token"),
    );

    return (
        <PageLayout
            headerSubtitle="Internal configuration"
            headerAction={
                <Button
                    asChild
                    variant="ghost"
                >
                    <RouterLink to="/">
                        <LuArrowLeft />
                        Public view
                    </RouterLink>
                </Button>
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