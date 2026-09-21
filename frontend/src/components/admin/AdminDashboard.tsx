import {useEffect, useState} from "react";
import {
    Alert,
    Badge,
    Box,
    Button,
    Container,
    Heading, Spinner,
    Stack,
    Tabs,
    Text, VStack,
} from "@chakra-ui/react";

import {
    LuActivity,
    LuBusFront,
    LuCalendarClock,
    LuMapPin,
    LuSave, LuSettings2,
} from "react-icons/lu";

import {getAdminConfig, updateAdminConfig} from "../../api/seebusApi";

import type {AdminConfig} from "../../types/adminConfig";
import {AdminHeader} from "./AdminHeader.tsx";
import {StationsTab} from "./tabs/StationsTab.tsx";
import {BusesTab} from "./tabs/BusesTab.tsx";
import {ScheduleTab} from "./tabs/ScheduleTab.tsx";
import {PoliciesTab} from "./tabs/PoliciesTab";
import {ReadingsTab} from "./tabs/ReadingsTab";

interface AdminDashboardProps {
    adminToken: string;
}

export type ConfigUpdater = (
    updater: (config: AdminConfig) => AdminConfig,
) => void;

type SaveStatus = {
    type: "success" | "error";
    message: string;
} | null;

const emptyConfig: AdminConfig = {
    stations: [],
    buses: [],
    defaultSchedule: [],
};

export const AdminDashboard = (props: AdminDashboardProps) => {
    const {adminToken,} = props;

    const [config, setConfig] = useState<AdminConfig>(emptyConfig);
    const [loading, setLoading] = useState(true);
    const [dirty, setDirty] = useState(false);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState<SaveStatus>(null);
    const [policyCount, setPolicyCount] = useState(0);
    const [readingCount, setReadingCount] = useState(0);

    useEffect(() => {
        let cancelled = false;

        const loadConfig = async () => {
            try {
                const loadedConfig =
                    await getAdminConfig(adminToken);

                if (cancelled) {
                    return;
                }

                setConfig(loadedConfig);
                setDirty(false);
            } catch {
                if (!cancelled) {
                    setStatus({
                        type: "error",
                        message: "Could not load configuration",
                    });
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };

        void loadConfig();

        return () => {
            cancelled = true;
        };
    }, [adminToken]);

    const updateConfig: ConfigUpdater = (updater) => {
        setConfig(updater);
        setDirty(true);
        setStatus(null);
    };

    const save = async () => {
        setSaving(true);
        setStatus(null);

        try {
            await updateAdminConfig(
                config,
                adminToken,
            );

            setDirty(false);

            setStatus({
                type: "success",
                message: "Configuration saved successfully",
            });
        } catch (error) {
            setStatus({
                type: "error",
                message:
                    error instanceof Error
                        ? error.message
                        : "Could not save configuration",
            });
        } finally {
            setSaving(false);
        }
    };

    return (
        <Box
            minH="100vh"
            bg="#050d20"
        >
            <AdminHeader/>

            { loading && (
                <VStack colorPalette="teal">
                    <Spinner color="colorPalette.600" size="xl"/>
                    <Text color="colorPalette.600">Loading...</Text>
                </VStack>
            )}

            <Container
                maxW="7xl"
                py="8"
            >
                <Stack gap="6">
                    <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="flex-start"
                        gap="4"
                    >
                        <Box>
                            <Heading size="2xl">
                                System configuration
                            </Heading>

                            <Text
                                color="fg.muted"
                                mt="1"
                            >
                                Manage stations, buses, policies, and the default SeeBus schedule
                            </Text>
                        </Box>

                        <Button
                            colorPalette="teal"
                            disabled={!dirty}
                            loading={saving}
                            loadingText="Saving"
                            onClick={() => void save()}
                        >
                            <LuSave />
                            Save changes
                        </Button>
                    </Box>

                    <Tabs.Root
                        defaultValue="stations"
                        variant="enclosed"
                        colorPalette="teal"
                    >
                        <Tabs.List>
                            <Tabs.Trigger value="stations">
                                <LuMapPin />

                                Stations

                                <Badge
                                    ml="2"
                                    variant="subtle"
                                >
                                    {config.stations.length}
                                </Badge>
                            </Tabs.Trigger>

                            <Tabs.Trigger value="buses">
                                <LuBusFront />

                                Buses

                                <Badge
                                    ml="2"
                                    variant="subtle"
                                >
                                    {config.buses.length}
                                </Badge>
                            </Tabs.Trigger>

                            <Tabs.Trigger value="schedule">
                                <LuCalendarClock />

                                Schedule

                                <Badge
                                    ml="2"
                                    variant="subtle"
                                >
                                    {config.defaultSchedule.length}
                                </Badge>
                            </Tabs.Trigger>

                            <Tabs.Trigger value="policies">
                                <LuSettings2 />

                                Policies

                                <Badge ml="2" variant="subtle">
                                    {policyCount}
                                </Badge>
                            </Tabs.Trigger>

                            <Tabs.Trigger value="readings">
                                <LuActivity />

                                Readings

                                <Badge ml="2" variant="subtle">
                                    {readingCount}
                                </Badge>
                            </Tabs.Trigger>
                        </Tabs.List>

                        <Tabs.Content value="stations">
                            <StationsTab
                                config={config}
                                updateConfig={updateConfig}
                            />
                        </Tabs.Content>

                        <Tabs.Content value="buses">
                            <BusesTab
                                config={config}
                                updateConfig={updateConfig}
                            />
                        </Tabs.Content>

                        <Tabs.Content value="schedule">
                            <ScheduleTab
                                config={config}
                                updateConfig={updateConfig}
                            />
                        </Tabs.Content>

                        <Tabs.Content value="policies">
                            <PoliciesTab
                                adminToken={adminToken}
                                onCountChange={setPolicyCount}
                            />
                        </Tabs.Content>

                        <Tabs.Content value="readings">
                            <ReadingsTab
                                adminToken={adminToken}
                                config={config}
                                onCountChange={setReadingCount}
                            />
                        </Tabs.Content>
                    </Tabs.Root>

                    {status && (
                        <Alert.Root
                            status={status.type}
                            variant="surface"
                        >
                            <Alert.Indicator />

                            <Alert.Content>
                                <Alert.Title>
                                    {status.type === "success"
                                        ? "Saved"
                                        : "Save failed"}
                                </Alert.Title>

                                <Alert.Description>
                                    {status.message}
                                </Alert.Description>
                            </Alert.Content>
                        </Alert.Root>
                    )}
                </Stack>
            </Container>
        </Box>
    );
};