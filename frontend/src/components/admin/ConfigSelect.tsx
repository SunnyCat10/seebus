import {
    Portal,
    Select,
    useListCollection,
} from "@chakra-ui/react";

interface ConfigSelectItem {
    label: string;
    value: string;
}

interface ConfigSelectProps {
    items: ConfigSelectItem[];
    value: string;
    placeholder: string;
    onChange: (value: string) => void;
}

export const ConfigSelect = (props: ConfigSelectProps) => {
    const {items, value, placeholder, onChange} = props;

    const {collection,} = useListCollection({initialItems: items});

    return (
        <Select.Root
            collection={collection}
            value={value ? [value] : []}
            size="sm"
            variant="outline"
            onValueChange={(details) => {
                onChange(details.value[0] ?? "");
            }}
        >
            <Select.HiddenSelect />

            <Select.Control>
                <Select.Trigger>
                    <Select.ValueText
                        placeholder={placeholder}
                    />
                </Select.Trigger>

                <Select.IndicatorGroup>
                    <Select.Indicator />
                </Select.IndicatorGroup>
            </Select.Control>

            <Portal>
                <Select.Positioner>
                    <Select.Content>
                        {collection.items.map((item) => (
                            <Select.Item
                                key={item.value}
                                item={item}
                            >
                                <Select.ItemText>
                                    {item.label}
                                </Select.ItemText>

                                <Select.ItemIndicator />
                            </Select.Item>
                        ))}
                    </Select.Content>
                </Select.Positioner>
            </Portal>
        </Select.Root>
    );
};