import { useEffect, useState } from "react";

import { getCurrentSchedule } from "../api/seebusApi";
import type { CurrentSchedule } from "../types/schedule";
import {Box, Container, Heading, IconButton, Stack, Text} from "@chakra-ui/react";
import {ScheduleCard} from "../components/schedule/ScheduleCard.tsx";
import {PageLayout} from "../components/layout/PageLayout.tsx";
import {LuSettings} from "react-icons/lu";
import {Link as RouterLink} from "react-router-dom";

export function SchedulePage() {
    const [schedule, setSchedule] = useState<CurrentSchedule | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [now, setNow] = useState(() => new Date());

    useEffect(() => {
        async function loadSchedule() {
            try {
                const result = await getCurrentSchedule();

                setSchedule(result);
                setError(null);
            } catch {
                setError("Could not load the current schedule");
            }
        }

        void loadSchedule();

        const interval = setInterval(loadSchedule, 60000);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const interval = setInterval(() => {
            setNow(new Date());
        }, 30_000);

        return () => clearInterval(interval);
    }, []);

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
                py={{ base: "6", md: "8" }}
            >
                <Box maxW="3xl">
                    <Heading size="xl" mb="1">
                        Upcoming buses
                    </Heading>

                    <Text color="gray.400" mb="6">
                        {now.toLocaleDateString(undefined, { weekday: "long" })}
                        {" · "}
                        {now.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                        })}
                    </Text>

                    <Stack gap="3">
                        {schedule?.entries.map((entry, index) => (
                            <ScheduleCard
                                key={`${entry.bus.id}-${entry.station.id}-${entry.arrivalTime}`}
                                arrivalTime={entry.arrivalTime}
                                station={entry.station.name}
                                bus={entry.bus.name}
                                next={index === 0}
                                now={now}
                            />
                        ))}
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
                            <Text>Loading...</Text>
                        </Box>
                    )}
                </Box>
            </Container>
        </PageLayout>
    );
}