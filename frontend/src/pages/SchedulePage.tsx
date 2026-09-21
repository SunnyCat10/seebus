import {useEffect, useState} from "react";

import {
    Box,
    Flex,
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
            contentPy={{
                base: "2",
                md: "3",
            }}
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
                <Box
                    maxW="3xl"
                    mx="auto"
                    w="full"
                    pb="8"
                >
                    <Box
                        mb="4"
                        bg="rgba(20, 32, 58, 0.92)"
                        borderWidth="1px"
                        borderColor="whiteAlpha.300"
                        borderRadius="xl"
                        px={{
                            base: "5",
                            md: "7",
                        }}
                        py="4"
                        boxShadow="0 6px 18px rgba(0, 0, 0, 0.16)"
                        backdropFilter="blur(8px)"
                    >
                        <Flex
                            justify="space-between"
                            align="center"
                            gap="6"
                        >
                            <Text
                                fontSize={{
                                    base: "lg",
                                    md: "xl",
                                }}
                                fontWeight="semibold"
                                color="whiteAlpha.950"
                            >
                                Upcoming buses
                            </Text>

                            <Stack
                                gap="0"
                                align="center"
                                minW="96px"
                            >
                                <Text
                                    fontSize={{
                                        base: "2xl",
                                        md: "3xl",
                                    }}
                                    fontWeight="semibold"
                                    lineHeight="0.95"
                                    color="whiteAlpha.800"
                                >
                                    {currentTime}
                                </Text>

                                <Text
                                    mt="1"
                                    fontSize="sm"
                                    fontWeight="medium"
                                    color="whiteAlpha.600"
                                >
                                    {weekday}
                                </Text>
                            </Stack>
                        </Flex>
                    </Box>

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
        </PageLayout>
    );
}