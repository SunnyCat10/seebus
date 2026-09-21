import {useEffect, useState} from "react";

import {
    Box,
    Container,
    Flex,
    Heading,
    IconButton,
    Stack,
    Text,
} from "@chakra-ui/react";

import {LuSettings} from "react-icons/lu";
import {Link as RouterLink} from "react-router-dom";
import {getCurrentSchedule} from "../api/seebusApi";
import type {CurrentSchedule} from "../types/schedule";
import {ScheduleCard} from "../components/schedule/ScheduleCard";
import {PageLayout} from "../components/layout/PageLayout";

export const SchedulePage = () => {
    const [schedule, setSchedule] = useState<CurrentSchedule | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [now, setNow] = useState(() => new Date());

    useEffect(() => {
        const loadSchedule = async () => {
            try {
                const result =
                    await getCurrentSchedule();

                setSchedule(result);
                setError(null);
            } catch {
                setError(
                    "Could not load the current schedule",
                );
            }
        }

        void loadSchedule();

        const interval =
            window.setInterval(
                () => void loadSchedule(),
                5_000,
            );

        return () =>
            window.clearInterval(interval);
    }, []);

    useEffect(() => {
        const interval =
            window.setInterval(
                () => {
                    setNow(new Date());
                },
                15_000,
            );

        return () =>
            window.clearInterval(interval);
    }, []);

    const currentTime =
        now.toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
            },
        );

    const weekday =
        now.toLocaleDateString(
            undefined,
            {
                weekday: "long",
            },
        );

    return (
        <PageLayout
            headerAction={
                <IconButton
                    asChild
                    aria-label="Admin settings"
                    variant="ghost"
                >
                    <RouterLink to="/admin">
                        <LuSettings />
                    </RouterLink>
                </IconButton>
            }
        >
            <Container
                position="relative"
                zIndex="1"
                maxW="5xl"
                py={{
                    base: "6",
                    md: "8",
                }}
            >
                <Box maxW="3xl">
                    <Heading
                        size="2xl"
                    >
                        Upcoming buses
                    </Heading>

                    <Flex
                        mt="2"
                        mb="7"
                        gap="3"
                        align="baseline"
                    >
                        <Text
                            fontSize="2xl"
                            fontWeight="bold"
                        >
                            {currentTime}
                        </Text>

                        <Text
                            color="fg.muted"
                            fontSize="md"
                        >
                            {weekday}
                        </Text>
                    </Flex>

                    <Stack gap="3">
                        {schedule?.entries.map(
                            (entry) => (
                                <ScheduleCard
                                    key={
                                        `${entry.bus.id}-` +
                                        `${entry.station.id}-` +
                                        `${entry.arrivalTime}`
                                    }
                                    arrivalTime={
                                        entry.arrivalTime
                                    }
                                    station={
                                        entry.station.name
                                    }
                                    bus={
                                        entry.bus.name
                                    }
                                    now={now}
                                />
                            ),
                        )}
                    </Stack>

                    {error && (
                        <Box
                            mt="5"
                            borderWidth="1px"
                            borderRadius="lg"
                            p="4"
                        >
                            <Text color="red.300">
                                {error}
                            </Text>
                        </Box>
                    )}

                    {!schedule && !error && (
                        <Box
                            mt="5"
                            borderWidth="1px"
                            borderRadius="lg"
                            p="4"
                        >
                            <Text>
                                Loading...
                            </Text>
                        </Box>
                    )}
                </Box>
            </Container>
        </PageLayout>
    );
}