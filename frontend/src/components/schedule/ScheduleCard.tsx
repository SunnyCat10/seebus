import {
    Box,
    Flex,
    HStack,
    Stack,
    Text,
} from "@chakra-ui/react";

interface ScheduleCardProps {
    arrivalTime: string;
    station: string;
    bus: string;
    now: Date;
}

const getBusColor = (bus: string): string => {
    const number = Number(bus);

    if (Number.isNaN(number)) {
        return "#334155";
    }

    if (number <= 20) {
        return "#760f22";
    }

    if (number <= 50) {
        return "#2563EB";
    }

    if (number <= 80) {
        return "#86198F";
    }

    if (number <= 100) {
        return "#C2410C";
    }

    if (number <= 200) {
        return "#00771b";
    }

    return "#475569";
};

interface EtaProps {
    minutes: number;
}

const Eta = ({minutes}: EtaProps) => {
    const hasHours = minutes >= 60;
    const hours = Math.floor(minutes / 60);

    const remainingMinutes =
        hasHours
            ? minutes % 60
            : minutes;

    const arriving = minutes <= 1;

    const minuteNumberColor =
        arriving
            ? "red.200"
            : hasHours
                ? "whiteAlpha.650"
                : "white";

    const minuteLabelColor =
        arriving
            ? "red.200"
            : hasHours
                ? "whiteAlpha.450"
                : "whiteAlpha.700";

    return (
        <HStack
            gap={{
                base: "5",
                md: "7",
            }}
            align="flex-end"
            justify="flex-end"
        >
            <Stack
                gap="0"
                align="center"
                minW="56px"
                visibility={
                    hasHours
                        ? "visible"
                        : "hidden"
                }
                aria-hidden={!hasHours}
            >
                <Text
                    fontSize={{
                        base: "4xl",
                        md: "5xl",
                    }}
                    fontWeight="bold"
                    lineHeight="0.9"
                    color="whiteAlpha.650"
                >
                    {hours}
                </Text>

                <Text
                    mt="1"
                    fontSize="xs"
                    fontWeight="bold"
                    color="whiteAlpha.450"
                >
                    hours
                </Text>
            </Stack>

            <Stack
                gap="0"
                align="center"
                minW="56px"
            >
                <Text
                    fontSize={{
                        base: "4xl",
                        md: "5xl",
                    }}
                    fontWeight="bold"
                    lineHeight="0.9"
                    color={minuteNumberColor}
                >
                    {remainingMinutes}
                </Text>

                <Text
                    mt="1"
                    fontSize={
                        hasHours
                            ? "xs"
                            : "sm"
                    }
                    fontWeight="bold"
                    color={minuteLabelColor}
                    opacity={
                        arriving
                            ? 0.72
                            : 1
                    }
                >
                    minutes
                </Text>
            </Stack>
        </HStack>
    );
};

export const ScheduleCard = (
    props: ScheduleCardProps,
) => {
    const {
        arrivalTime,
        station,
        bus,
        now,
    } = props;

    const arrival =
        new Date(arrivalTime);

    const minutesUntil =
        Math.max(
            0,
            Math.ceil(
                (
                    arrival.getTime() -
                    now.getTime()
                ) / 60_000,
            ),
        );

    const backgroundColor =
        getBusColor(bus);

    return (
        <Box
            bg={backgroundColor}
            borderRadius="xl"
            px={{
                base: "5",
                md: "7",
            }}
            py={{
                base: "5",
                md: "6",
            }}
            borderWidth="1px"
            borderColor="whiteAlpha.300"
            boxShadow="0 8px 24px rgba(0, 0, 0, 0.22)"
        >
            <Flex
                justify="space-between"
                align="center"
                gap="6"
            >
                <Stack
                    gap="2"
                    minW="0"
                >
                    <Text
                        fontSize={{
                            base: "4xl",
                            md: "5xl",
                        }}
                        fontWeight="bold"
                        lineHeight="0.9"
                        color="white"
                    >
                        {bus}
                    </Text>

                    <Text
                        fontSize={{
                            base: "lg",
                            md: "2xl",
                        }}
                        fontWeight="semibold"
                        lineHeight="1"
                        color="whiteAlpha.950"
                        truncate
                    >
                        {station}
                    </Text>
                </Stack>

                <Eta
                    minutes={minutesUntil}
                />
            </Flex>
        </Box>
    );
};