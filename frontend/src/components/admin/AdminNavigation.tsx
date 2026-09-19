import type {Section} from "./AdminDashboard.tsx";
import {Button, HStack, Stack, Text} from "@chakra-ui/react";
import {LuBusFront, LuCalendarClock, LuMapPin} from "react-icons/lu";
import type {ReactNode} from "react";


export interface AdminNavigationProps {
    section: Section;
    setSection: (section: Section) => void;
    stations: number;
    buses: number;
    schedule: number;
}

export interface NavButtonProps {
    active: boolean;
    icon: ReactNode;
    label: string;
    count: number;
    onClick: () => void;
}

export const AdminNavigation = (props : AdminNavigationProps) => {
    const { section, setSection, stations, buses, schedule,} = props;

    return (
        <Stack
            gap="2"
            direction={{
                base: "row",
                md: "column",
            }}
            overflowX={{
                base: "auto",
                md: "visible",
            }}
        >
            <NavButton
                active={section === "stations"}
                icon={<LuMapPin />}
                label="Stations"
                count={stations}
                onClick={() =>
                    setSection("stations")
                }
            />

            <NavButton
                active={section === "buses"}
                icon={<LuBusFront />}
                label="Buses"
                count={buses}
                onClick={() =>
                    setSection("buses")
                }
            />

            <NavButton
                active={section === "schedule"}
                icon={<LuCalendarClock />}
                label="Schedule"
                count={schedule}
                onClick={() =>
                    setSection("schedule")
                }
            />
        </Stack>
    );
}

const NavButton = (props: NavButtonProps) => {
    const {active, icon, label, count, onClick} = props;

    return (
        <Button
            variant="ghost"
            justifyContent="space-between"
            minW={{ base: "150px", md: "100%" }}
            bg={
                active
                    ? "rgba(34, 199, 184, 0.10)"
                    : "transparent"
            }
            color={
                active
                    ? "teal.300"
                    : "gray.400"
            }
            borderWidth="1px"
            borderColor={
                active
                    ? "teal.800"
                    : "transparent"
            }
            onClick={onClick}
        >
            <HStack>
                {icon}
                <Text>{label}</Text>
            </HStack>

            <Text
                fontSize="xs"
                color="gray.500"
            >
                {count}
            </Text>
        </Button>
    );
}