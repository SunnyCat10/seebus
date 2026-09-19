import { useEffect, useState } from "react";

import { getCurrentSchedule } from "../api/seebusApi";
import type { CurrentSchedule } from "../types/schedule";
import {Box, Container, Heading, Stack, Text} from "@chakra-ui/react";
import {ScheduleCard} from "../components/schedule/ScheduleCard.tsx";
import {TransitBackground} from "../components/background/TransitBackground.tsx";
import {AppHeader} from "../components/layout/AppHeader.tsx";

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
        <Box
            minH="100vh"
            bg="#080e20"
            position="relative"
        >
            <TransitBackground />

            <AppHeader/>

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
        </Box>
    );
}