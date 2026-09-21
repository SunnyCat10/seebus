import {DateInput} from "@chakra-ui/react";
import {
    CalendarDateTime,
    DateFormatter,
} from "@internationalized/date";

interface ScheduleTimeInputProps {
    value: string;
    onChange: (value: string) => void;
}

const formatter = new DateFormatter(
    "en-GB",
    {
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
    },
);

const parseTime = (value: string): CalendarDateTime[] => {
    if (!value) {
        return [];
    }

    const parts = value.split(":");

    if (parts.length < 2) {
        return [];
    }

    const hour = Number(parts[0]);
    const minute = Number(parts[1]);

    if (
        Number.isNaN(hour) ||
        Number.isNaN(minute) ||
        hour < 0 ||
        hour > 23 ||
        minute < 0 ||
        minute > 59
    ) {
        return [];
    }

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
    return (
        `${String(hour).padStart(2, "0")}:` +
        `${String(minute).padStart(2, "0")}`
    );
};

export const ScheduleTimeInput = (props: ScheduleTimeInputProps) => {
    const {value, onChange} = props;

    return (
        <DateInput.Root
            value={parseTime(value)}
            granularity="minute"
            formatter={formatter}
            hourCycle={24}
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