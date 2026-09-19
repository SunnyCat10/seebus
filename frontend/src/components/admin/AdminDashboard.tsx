import { useState } from "react";
import {
    Alert,
    Badge,
    Box,
    Button,
    Container,
    Flex,
    Heading,
    HStack,
    Stack,
    Tabs,
    Text,
} from "@chakra-ui/react";

import {
    LuBusFront,
    LuCalendarClock,
    LuMapPin,
    LuSave,
} from "react-icons/lu";

import { updateAdminConfig } from "../../api/seebusApi";

import type {AdminConfig} from "../../types/adminConfig";
import {AdminHeader} from "./AdminHeader.tsx";
import {StationsTab} from "./tabs/StationsTab.tsx";
import {BusesTab} from "./tabs/BusesTab.tsx";
import {ScheduleTab} from "./tabs/ScheduleTab.tsx";

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

    const [config, setConfig] =
        useState<AdminConfig>(emptyConfig);

    const [dirty, setDirty] =
        useState(false);

    const [saving, setSaving] =
        useState(false);

    const [status, setStatus] =
        useState<SaveStatus>(null);

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

            <Container
                maxW="7xl"
                py="8"
            >
                <Stack gap="6">
                    <Box>
                        <Heading size="2xl">
                            System configuration
                        </Heading>

                        <Text
                            color="fg.muted"
                            mt="1"
                        >
                            Manage stations, buses, and the
                            default SeeBus schedule
                        </Text>
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

                    <Flex
                        position="sticky"
                        bottom="0"
                        zIndex="10"
                        justify="space-between"
                        align="center"
                        px="5"
                        py="4"
                        borderWidth="1px"
                        borderColor="whiteAlpha.200"
                        borderRadius="xl"
                        bg="rgba(5, 13, 32, 0.94)"
                        backdropFilter="blur(12px)"
                    >
                        <HStack gap="3">
                            <Text color="fg.muted">
                                Configuration status
                            </Text>

                            <Badge
                                colorPalette={
                                    dirty
                                        ? "orange"
                                        : "green"
                                }
                            >
                                {dirty
                                    ? "Unsaved changes"
                                    : "Up to date"}
                            </Badge>
                        </HStack>

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
                    </Flex>
                </Stack>
            </Container>
        </Box>
    );
};