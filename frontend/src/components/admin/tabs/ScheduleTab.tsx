import {Alert, Box, Button, Card, EmptyState, Flex, IconButton, Input, NativeSelect, Table} from "@chakra-ui/react";
import type {AdminConfig, ScheduleEntryConfig} from "../../../types/adminConfig.ts";
import type {ConfigUpdater} from "../AdminDashboard.tsx";
import {LuCalendarClock, LuPlus, LuTrash2} from "react-icons/lu";

export interface ScheduleTabProps {
    config: AdminConfig;
    updateConfig: ConfigUpdater;
}

export const ScheduleTab = (props: ScheduleTabProps) => {
    const {config, updateConfig} = props;

    const canAdd =
        config.stations.length > 0 &&
        config.buses.length > 0;

    const addEntry = () => {
        if (!canAdd) {
            return;
        }

        updateConfig((current) => ({
            ...current,

            defaultSchedule: [
                ...current.defaultSchedule,
                {
                    busId:
                        current.buses[0]?.id ?? "",
                    stationId:
                        current.stations[0]?.id ?? "",
                    time: "12:00",
                },
            ],
        }));
    };

    const updateEntry = (index: number, patch: Partial<ScheduleEntryConfig>) => {
        updateConfig((current) => ({
            ...current,

            defaultSchedule:
                current.defaultSchedule.map(
                    (entry: any, currentIndex: number) =>
                        currentIndex === index
                            ? {
                                ...entry,
                                ...patch,
                            }
                            : entry,
                ),
        }));
    };

    const removeEntry = (index: number) => {
        updateConfig((current) => ({
            ...current,

            defaultSchedule:
                current.defaultSchedule.filter(
                    (_: any, currentIndex: number) =>
                        currentIndex !== index,
                ),
        }));
    };

    return (
        <Card.Root mt="4">
            <Card.Header>
                <Flex
                    justify="space-between"
                    align="center"
                >
                    <Box>
                        <Card.Title>
                            Default schedule
                        </Card.Title>

                        <Card.Description>
                            Base schedule used before dynamic
                            policies modify service.
                        </Card.Description>
                    </Box>

                    <Button
                        size="sm"
                        colorPalette="teal"
                        variant="outline"
                        disabled={!canAdd}
                        onClick={addEntry}
                    >
                        <LuPlus />

                        Add entry
                    </Button>
                </Flex>
            </Card.Header>

            <Card.Body>
                {!canAdd ? (
                    <Alert.Root
                        status="info"
                        variant="surface"
                    >
                        <Alert.Indicator />

                        <Alert.Content>
                            <Alert.Title>
                                Schedule unavailable
                            </Alert.Title>

                            <Alert.Description>
                                Add at least one station and one
                                bus before creating schedule
                                entries
                            </Alert.Description>
                        </Alert.Content>
                    </Alert.Root>
                ) : config.defaultSchedule.length === 0 ? (
                    <EmptyState.Root>
                        <EmptyState.Content>
                            <EmptyState.Indicator>
                                <LuCalendarClock />
                            </EmptyState.Indicator>

                            <EmptyState.Title>
                                No schedule entries
                            </EmptyState.Title>

                            <EmptyState.Description>
                                Create the first entry in the
                                default schedule
                            </EmptyState.Description>

                            <Button
                                colorPalette="teal"
                                variant="outline"
                                onClick={addEntry}
                            >
                                <LuPlus />

                                Add entry
                            </Button>
                        </EmptyState.Content>
                    </EmptyState.Root>
                ) : (
                    <Table.Root
                        variant="outline"
                        interactive
                    >
                        <Table.Header>
                            <Table.Row>
                                <Table.ColumnHeader>
                                    Bus
                                </Table.ColumnHeader>

                                <Table.ColumnHeader>
                                    Station
                                </Table.ColumnHeader>

                                <Table.ColumnHeader
                                    width="180px"
                                >
                                    Time
                                </Table.ColumnHeader>

                                <Table.ColumnHeader
                                    width="70px"
                                />
                            </Table.Row>
                        </Table.Header>

                        <Table.Body>
                            {config.defaultSchedule.map(
                                (entry, index) => (
                                    <Table.Row
                                        key={`${entry.busId}-${entry.stationId}-${entry.time}-${index}`}
                                    >
                                        <Table.Cell>
                                            <NativeSelect.Root
                                                size="sm"
                                            >
                                                <NativeSelect.Field
                                                    value={
                                                        entry.busId
                                                    }
                                                    onChange={(event) =>
                                                        updateEntry(
                                                            index,
                                                            {
                                                                busId:
                                                                event
                                                                    .target
                                                                    .value,
                                                            },
                                                        )
                                                    }
                                                >
                                                    {config.buses.map(
                                                        (
                                                            bus,
                                                        ) => (
                                                            <option
                                                                key={
                                                                    bus.id
                                                                }
                                                                value={
                                                                    bus.id
                                                                }
                                                            >
                                                                {bus.name ||
                                                                    bus.id}
                                                            </option>
                                                        ),
                                                    )}
                                                </NativeSelect.Field>

                                                <NativeSelect.Indicator />
                                            </NativeSelect.Root>
                                        </Table.Cell>

                                        <Table.Cell>
                                            <NativeSelect.Root
                                                size="sm"
                                            >
                                                <NativeSelect.Field
                                                    value={
                                                        entry.stationId
                                                    }
                                                    onChange={(
                                                        event,
                                                    ) =>
                                                        updateEntry(
                                                            index,
                                                            {
                                                                stationId:
                                                                event
                                                                    .target
                                                                    .value,
                                                            },
                                                        )
                                                    }
                                                >
                                                    {config.stations.map(
                                                        (
                                                            station,
                                                        ) => (
                                                            <option
                                                                key={
                                                                    station.id
                                                                }
                                                                value={
                                                                    station.id
                                                                }
                                                            >
                                                                {station.name ||
                                                                    station.id}
                                                            </option>
                                                        ),
                                                    )}
                                                </NativeSelect.Field>

                                                <NativeSelect.Indicator />
                                            </NativeSelect.Root>
                                        </Table.Cell>

                                        <Table.Cell>
                                            <Input
                                                size="sm"
                                                type="time"
                                                value={
                                                    entry.time
                                                }
                                                onChange={(event) =>
                                                    updateEntry(
                                                        index,
                                                        {
                                                            time:
                                                            event
                                                                .target
                                                                .value,
                                                        },
                                                    )
                                                }
                                            />
                                        </Table.Cell>

                                        <Table.Cell
                                            textAlign="right"
                                        >
                                            <IconButton
                                                aria-label="Delete schedule entry"
                                                size="sm"
                                                variant="ghost"
                                                colorPalette="red"
                                                onClick={() => removeEntry(index)
                                                }
                                            >
                                                <LuTrash2 />
                                            </IconButton>
                                        </Table.Cell>
                                    </Table.Row>
                                ),
                            )}
                        </Table.Body>
                    </Table.Root>
                )}
            </Card.Body>
        </Card.Root>
    );
};