import { DateInput } from "@chakra-ui/react";
import {
    CalendarDateTime,
    DateFormatter,
} from "@internationalized/date";

interface ScheduleTimeInputProps {
    value: string;
    onChange: (value: string) => void;
}

const formatter = new DateFormatter(
    "en-US",
    {
        hour: "numeric",
        minute: "2-digit",
    },
);

const parseTime = (
    value: string,
): CalendarDateTime[] => {
    const match =
        /^(\d{2}):(\d{2})$/.exec(value);

    if (!match) {
        return [];
    }

    const hour = Number(match[1]);
    const minute = Number(match[2]);

    return [
        new CalendarDateTime(
            2000,
            1,
            1,
            hour,
            minute,
        ),
    ];
};

const formatTime = (
    hour: number,
    minute: number,
) => {
    return `${String(hour).padStart(2, "0")}:${String(
        minute,
    ).padStart(2, "0")}`;
};

export const ScheduleTimeInput = (
    props: ScheduleTimeInputProps,
) => {
    const {
        value,
        onChange,
    } = props;

    return (
        <DateInput.Root
            value={parseTime(value)}
            granularity="minute"
            formatter={formatter}
            hourCycle={12}
            shouldForceLeadingZeros
            size="sm"
            onValueChange={(details) => {
                const selected =
                    details.value[0];

                if (
                    !selected ||
                    !("hour" in selected) ||
                    !("minute" in selected)
                ) {
                    return;
                }

                onChange(
                    formatTime(
                        selected.hour,
                        selected.minute,
                    ),
                );
            }}
        >
            <DateInput.Control>
                <DateInput.Segments />
            </DateInput.Control>

            <DateInput.HiddenInput />
        </DateInput.Root>
    );
};