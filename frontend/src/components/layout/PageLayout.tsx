import type {ReactNode} from "react";

import {
    Box,
    Container,
    Flex,
    Icon,
    Stack,
    Text,
} from "@chakra-ui/react";

import {LuBusFront} from "react-icons/lu";
import {TransitBackground} from "../background/TransitBackground.tsx";

interface PageLayoutProps {
    children: ReactNode;
    headerAction?: ReactNode;
    headerSubtitle?: string;
    maxW?: string;
}

export const PageLayout = (props : PageLayoutProps) => {
    const {children, headerAction, headerSubtitle, maxW = "7xl"} = props;

    return (
        <Box
            minH="100vh"
            bg="#050d20"
            position="relative"
            overflow="hidden"
        >
            <Box
                position="absolute"
                top="64px"
                left="0"
                right="0"
                bottom="0"
                bgImage="url('/transit-map.svg')"
                bgPos="center top"
                bgSize="cover"
                bgRepeat="no-repeat"
                opacity="0.28"
                pointerEvents="none"
            >
                <TransitBackground/>
            </Box>

            <Box
                position="relative"
                zIndex="1"
            >
                <Box
                    h="64px"
                    bg="#020817"
                    borderBottomWidth="1px"
                    borderColor="whiteAlpha.100"
                >
                    <Flex
                        h="full"
                        px="6"
                        align="center"
                        justify="space-between"
                    >
                        <Flex
                            align="center"
                            gap="3"
                        >
                            <Flex
                                boxSize="38px"
                                align="center"
                                justify="center"
                                borderWidth="1px"
                                borderColor="teal.500"
                                borderRadius="lg"
                                color="teal.300"
                            >
                                <Icon
                                    as={LuBusFront}
                                    boxSize="20px"
                                />
                            </Flex>

                            <Stack gap="0">
                                <Text
                                    fontWeight="semibold"
                                    fontSize="lg"
                                >
                                    SeeBus
                                </Text>

                                {headerSubtitle && (
                                    <Text
                                        color="fg.muted"
                                        fontSize="xs"
                                    >
                                        {headerSubtitle}
                                    </Text>
                                )}
                            </Stack>
                        </Flex>

                        {headerAction}
                    </Flex>
                </Box>

                <Container
                    maxW={maxW}
                    py="8"
                >
                    {children}
                </Container>
            </Box>
        </Box>
    );
};