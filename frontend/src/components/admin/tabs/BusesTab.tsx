import {Button, EmptyState, IconButton, Input, NumberInput, Table} from "@chakra-ui/react";
import type {AdminConfig} from "../../../types/adminConfig.ts";
import type {Bus} from "../../../types/bus.ts";
import type {ConfigUpdater} from "../AdminDashboard.tsx";
import {LuBusFront, LuPlus, LuTrash2} from "react-icons/lu";
import {AdminTabLayout} from "../../layout/AdminTabLayout.tsx";

export interface BusesTabProps {
    config: AdminConfig;
    updateConfig: ConfigUpdater;
}

export const BusesTab = (props: BusesTabProps,) => {
    const {config, updateConfig} = props;

    const addBus = () => {
        updateConfig((current) => ({
            ...current,

            buses: [
                ...current.buses,
                {
                    id: "",
                    name: "",
                    capacity: 50,
                },
            ],
        }));
    };

    const updateBus = (index: number, patch: Partial<Bus>) => {
        updateConfig((current) => ({
            ...current,

            buses: current.buses.map(
                (bus: any, currentIndex: number) =>
                    currentIndex === index
                        ? {
                            ...bus,
                            ...patch,
                        }
                        : bus,
            ),
        }));
    };

    const removeBus = (index: number) => {
        updateConfig((current) => ({
            ...current,

            buses: current.buses.filter(
                (_: any, currentIndex: number) =>
                    currentIndex !== index,
            ),
        }));
    };

    return (
        <AdminTabLayout
            title="Buses"
            description="Vehicles available to the scheduler"
            action={
                <Button
                    size="sm"
                    colorPalette="teal"
                    variant="outline"
                    onClick={addBus}
                >
                    <LuPlus />
                    Add bus
                </Button>
            }
        >
                {config.buses.length === 0 ? (
                    <EmptyState.Root>
                        <EmptyState.Content>
                            <EmptyState.Indicator>
                                <LuBusFront />
                            </EmptyState.Indicator>

                            <EmptyState.Title>
                                No buses configured
                            </EmptyState.Title>

                            <EmptyState.Description>
                                Add a bus before creating the
                                default schedule
                            </EmptyState.Description>

                            <Button
                                colorPalette="teal"
                                variant="outline"
                                onClick={addBus}
                            >
                                <LuPlus />

                                Add bus
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
                                    Bus ID
                                </Table.ColumnHeader>

                                <Table.ColumnHeader>
                                    Name
                                </Table.ColumnHeader>

                                <Table.ColumnHeader
                                    width="180px"
                                >
                                    Capacity
                                </Table.ColumnHeader>

                                <Table.ColumnHeader
                                    width="70px"
                                />
                            </Table.Row>
                        </Table.Header>

                        <Table.Body>
                            {config.buses.map(
                                (bus, index) => (
                                    <Table.Row
                                        key={`${index}`}
                                    >
                                        <Table.Cell>
                                            <Input
                                                size="sm"
                                                value={bus.id}
                                                placeholder="bus-1"
                                                onChange={(event) =>
                                                    updateBus(
                                                        index,
                                                        {
                                                            id:
                                                            event
                                                                .target
                                                                .value,
                                                        },
                                                    )
                                                }
                                            />
                                        </Table.Cell>

                                        <Table.Cell>
                                            <Input
                                                size="sm"
                                                value={
                                                    bus.name
                                                }
                                                placeholder="Bus 1"
                                                onChange={(event) =>
                                                    updateBus(
                                                        index,
                                                        {
                                                            name:
                                                            event
                                                                .target
                                                                .value,
                                                        },
                                                    )
                                                }
                                            />
                                        </Table.Cell>

                                        <Table.Cell>
                                            <NumberInput.Root
                                                size="sm"
                                                min={1}
                                                value={String(
                                                    bus.capacity,
                                                )}
                                                onValueChange={(details) =>
                                                    updateBus(
                                                        index,
                                                        {
                                                            capacity:
                                                                Number(
                                                                    details.value,
                                                                ),
                                                        },
                                                    )
                                                }
                                            >
                                                <NumberInput.Input />

                                                <NumberInput.Control />
                                            </NumberInput.Root>
                                        </Table.Cell>

                                        <Table.Cell
                                            textAlign="right"
                                        >
                                            <IconButton
                                                aria-label="Delete bus"
                                                size="sm"
                                                variant="ghost"
                                                colorPalette="red"
                                                onClick={() =>
                                                    removeBus(
                                                        index,
                                                    )
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
        </AdminTabLayout>
    );
};