import {useEffect, useState} from "react";
import {
    Badge,
    Box,
    Heading,
    Spinner,
    Stack,
    Table,
    Text,
} from "@chakra-ui/react";

import {
    getLatestReadings,
    getReadings,
} from "../../../api/seebusApi";

import type {AdminConfig} from "../../../types/adminConfig";
import type {StationReading} from "../../../types/reading";

interface ReadingsTabProps {
    adminToken: string;
    config: AdminConfig;
    onCountChange?: (count: number) => void;
}

export const ReadingsTab = ( props : ReadingsTabProps) => {
    const {adminToken, config, onCountChange} = props;

    const [history, setHistory] = useState<StationReading[]>([]);
    const [latest, setLatest] = useState<Record<string, StationReading>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        const load = async () => {
            try {
                const [
                    loadedHistory,
                    loadedLatest,
                ] = await Promise.all([
                    getReadings(adminToken),
                    getLatestReadings(adminToken),
                ]);

                if (cancelled) {
                    return;
                }

                setHistory(loadedHistory);
                setLatest(loadedLatest);

                onCountChange?.(
                    loadedHistory.length,
                );

                setError(null);
            } catch (error) {
                if (!cancelled) {
                    setError(
                        error instanceof Error
                            ? error.message
                            : "Could not load readings",
                    );
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };

        void load();

        const interval =
            window.setInterval(
                () => void load(),
                5000,
            );

        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, [adminToken, onCountChange]);

    const getStationName = (
        stationId: string,
    ) => {
        return config.stations.find(
            station => station.id === stationId,
        )?.name ?? stationId;
    };

    const formatOccupancy = (
        occupancy: number,
    ) =>
        `${Math.round(occupancy * 100)}%`;

    const formatTime = (
        value: string,
    ) =>
        new Date(value).toLocaleString();

    if (loading) {
        return (
            <Box p="6">
                <Spinner />
            </Box>
        );
    }

    return (
        <Stack
            gap="6"
            mt="6"
        >
            {error && (
                <Text color="red.400">
                    {error}
                </Text>
            )}

            <Box
                borderWidth="1px"
                borderRadius="lg"
                p="6"
            >
                <Heading size="md">
                    Latest station readings
                </Heading>

                <Text
                    color="fg.muted"
                    mt="1"
                    mb="5"
                >
                    Most recent reading received from each
                    station
                </Text>

                <Table.Root>
                    <Table.Header>
                        <Table.Row>
                            <Table.ColumnHeader>
                                Station
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Occupancy
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Measured
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Received
                            </Table.ColumnHeader>
                        </Table.Row>
                    </Table.Header>

                    <Table.Body>
                        {Object.values(latest).map(
                            reading => (
                                <Table.Row key={reading.id}>
                                    <Table.Cell>
                                        {getStationName(
                                            reading.stationId,
                                        )}
                                    </Table.Cell>

                                    <Table.Cell>
                                        <Badge
                                            colorPalette={
                                                reading.occupancy >= 0.5
                                                    ? "orange"
                                                    : "teal"
                                            }
                                        >
                                            {formatOccupancy(
                                                reading.occupancy,
                                            )}
                                        </Badge>
                                    </Table.Cell>

                                    <Table.Cell>
                                        {formatTime(
                                            reading.measuredAt,
                                        )}
                                    </Table.Cell>

                                    <Table.Cell>
                                        {formatTime(
                                            reading.receivedAt,
                                        )}
                                    </Table.Cell>
                                </Table.Row>
                            ),
                        )}
                    </Table.Body>
                </Table.Root>
            </Box>

            <Box
                borderWidth="1px"
                borderRadius="lg"
                p="6"
            >
                <Heading size="md">
                    Reading history
                </Heading>

                <Text
                    color="fg.muted"
                    mt="1"
                    mb="5"
                >
                    Recent sensor readings retained by the
                    backend
                </Text>

                <Table.Root>
                    <Table.Header>
                        <Table.Row>
                            <Table.ColumnHeader>
                                Station
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Occupancy
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Measured
                            </Table.ColumnHeader>

                            <Table.ColumnHeader>
                                Received
                            </Table.ColumnHeader>
                        </Table.Row>
                    </Table.Header>

                    <Table.Body>
                        {[...history]
                            .reverse()
                            .map(reading => (
                                <Table.Row key={reading.id}>
                                    <Table.Cell>
                                        {getStationName(
                                            reading.stationId,
                                        )}
                                    </Table.Cell>

                                    <Table.Cell>
                                        {formatOccupancy(
                                            reading.occupancy,
                                        )}
                                    </Table.Cell>

                                    <Table.Cell>
                                        {formatTime(
                                            reading.measuredAt,
                                        )}
                                    </Table.Cell>

                                    <Table.Cell>
                                        {formatTime(
                                            reading.receivedAt,
                                        )}
                                    </Table.Cell>
                                </Table.Row>
                            ))}
                    </Table.Body>
                </Table.Root>
            </Box>
        </Stack>
    );
};