import {
    Box,
    Flex,
    Text,
} from "@chakra-ui/react";

interface ScheduleCardProps {
    arrivalTime: string;
    station: string;
    bus: string;
    next?: boolean;
    now: Date;
}

export function ScheduleCard(props : ScheduleCardProps) {
    const { arrivalTime, station, bus, next, now } = props;

    const arrival = new Date(arrivalTime);

    const minutesUntil = Math.max(
        0,
        Math.ceil(
            (arrival.getTime() - now.getTime()) / 60_000
        ),
    );

    const formattedTime = arrival.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    });

    return (
        <Box
            borderWidth="1px"
            borderColor={next ? "teal.400" : "whiteAlpha.200"}
            bg={next ? "rgba(8, 48, 42, 0.88)" : "rgba(18, 28, 52, 0.88)"}
            backdropFilter="blur(10px)"
            boxShadow="0 8px 24px rgba(0,0,0,0.22)"
            borderRadius="xl"
            px="5"
            py="4"
        >
            <Flex
                justify="space-between"
                align="center"
            >
                <Box>
                    <Text fontSize="lg" fontWeight="bold">
                        {formattedTime}
                    </Text>

                    <Text color="fg.muted">
                        {station}
                    </Text>
                </Box>

                <Box textAlign="right">
                    <Text fontWeight="semibold">
                        {bus}
                    </Text>

                    <Text
                        fontSize="sm"
                        color={
                            minutesUntil <= 5
                                ? "orange.300"
                                : "fg.muted"
                        }
                    >
                        {minutesUntil === 0
                            ? "Now"
                            : `${minutesUntil} min`}
                    </Text>
                </Box>
            </Flex>
        </Box>
    );
}