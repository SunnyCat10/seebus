import {Button, EmptyState, IconButton, Input, Table} from "@chakra-ui/react";
import type {AdminConfig} from "../../../types/adminConfig.ts";
import type {ConfigUpdater} from "../AdminDashboard.tsx"
import type {Station} from "../../../types/station.ts";
import {LuMapPin, LuPlus, LuTrash2} from "react-icons/lu";
import {AdminTabLayout} from "../../layout/AdminTabLayout.tsx";

export interface StationsTabProps {
    config: AdminConfig;
    updateConfig: ConfigUpdater;
}

export const StationsTab = (props: StationsTabProps) => {
    const {config, updateConfig} = props;

    const addStation = () => {
        updateConfig((current) => ({
            ...current,

            stations: [
                ...current.stations,
                {
                    id: "",
                    name: "",
                },
            ],
        }));
    };

    const updateStation = (index: number, patch: Partial<Station>) => {
        updateConfig((current) => ({
            ...current,

            stations: current.stations.map(
                (station: any, currentIndex: number) =>
                    currentIndex === index
                        ? {
                            ...station,
                            ...patch,
                        }
                        : station,
            ),
        }));
    };

    const removeStation = (index: number,) => {
        updateConfig((current) => ({
            ...current,

            stations: current.stations.filter(
                (_: any, currentIndex: number) =>
                    currentIndex !== index,
            ),
        }));
    };

    return (
        <AdminTabLayout
            title="Stations"
            description="Stations monitored by the SeeBus system."
            action={
                <Button
                    size="sm"
                        colorPalette="teal"
                        variant="outline"
                        onClick={addStation}>
                <LuPlus />
                Add station
                </Button>
            }
        >
                {config.stations.length === 0 ? (
                    <EmptyState.Root>
                        <EmptyState.Content>
                            <EmptyState.Indicator>
                                <LuMapPin />
                            </EmptyState.Indicator>

                            <EmptyState.Title>
                                No stations configured
                            </EmptyState.Title>

                            <EmptyState.Description>
                                Add a station to start building
                                the network.
                            </EmptyState.Description>

                            <Button
                                colorPalette="teal"
                                variant="outline"
                                onClick={addStation}
                            >
                                <LuPlus />

                                Add station
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
                                <Table.ColumnHeader
                                    width="35%"
                                >
                                    Station ID
                                </Table.ColumnHeader>

                                <Table.ColumnHeader>
                                    Name
                                </Table.ColumnHeader>

                                <Table.ColumnHeader
                                    width="70px"
                                />
                            </Table.Row>
                        </Table.Header>

                        <Table.Body>
                            {config.stations.map(
                                (station, index) => (
                                    <Table.Row
                                        key={`${index}`}
                                    >
                                        <Table.Cell>
                                            <Input
                                                size="sm"
                                                value={
                                                    station.id
                                                }
                                                placeholder="raft-station"
                                                onChange={(
                                                    event,
                                                ) =>
                                                    updateStation(
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
                                                    station.name
                                                }
                                                placeholder="Raft Station"
                                                onChange={(
                                                    event,
                                                ) =>
                                                    updateStation(
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

                                        <Table.Cell
                                            textAlign="right"
                                        >
                                            <IconButton
                                                aria-label="Delete station"
                                                size="sm"
                                                variant="ghost"
                                                colorPalette="red"
                                                onClick={() =>
                                                    removeStation(
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