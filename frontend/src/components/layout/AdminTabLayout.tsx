import type {ReactNode} from "react";
import {
    Box,
    Card,
    Flex,
} from "@chakra-ui/react";

interface AdminTabLayoutProps {
    title: string;
    description: string;
    action?: ReactNode;
    children: ReactNode;
}

export function AdminTabLayout(props : AdminTabLayoutProps) {
    const {title, description, action, children,} = props;

    return (
        <Card.Root mt="4">
            <Card.Header>
                <Flex
                    justify="space-between"
                    align="center"
                    gap="4"
                >
                    <Box>
                        <Card.Title>
                            {title}
                        </Card.Title>

                        <Card.Description>
                            {description}
                        </Card.Description>
                    </Box>

                    {action}
                </Flex>
            </Card.Header>

            <Card.Body>
                {children}
            </Card.Body>
        </Card.Root>
    );
}