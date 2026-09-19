import { Box } from "@chakra-ui/react";

type Node = {
    id: string;
    x: number;
    y: number;
};

type Route = {
    id: string;
    color: string;
    width: number;
    opacity?: number;
    stops: string[];
};

type Point = {
    x: number;
    y: number;
};

const nodes: Node[] = [
    { id: "c1", x: 690, y: 305 },
    { id: "c2", x: 825, y: 287 },
    { id: "c3", x: 962, y: 295 },
    { id: "c4", x: 1102, y: 318 },

    { id: "c5", x: 635, y: 422 },
    { id: "c6", x: 780, y: 405 },
    { id: "c7", x: 920, y: 418 },
    { id: "c8", x: 1058, y: 406 },
    { id: "c9", x: 1205, y: 438 },

    { id: "c10", x: 680, y: 555 },
    { id: "c11", x: 826, y: 535 },
    { id: "c12", x: 965, y: 548 },
    { id: "c13", x: 1112, y: 540 },

    { id: "c14", x: 760, y: 675 },
    { id: "c15", x: 906, y: 660 },
    { id: "c16", x: 1056, y: 686 },

    { id: "w1", x: -180, y: 420 },
    { id: "w2", x: -20, y: 420 },
    { id: "w3", x: 180, y: 420 },
    { id: "w4", x: 365, y: 420 },
    { id: "w5", x: 535, y: 420 },

    { id: "wl1", x: 60, y: 570 },
    { id: "wl2", x: 245, y: 568 },
    { id: "wl3", x: 455, y: 552 },

    { id: "nw1", x: 180, y: -140 },
    { id: "nw2", x: 275, y: 25 },
    { id: "nw3", x: 390, y: 145 },
    { id: "nw4", x: 535, y: 235 },
    { id: "nw5", x: 625, y: 282 },

    { id: "n1", x: 760, y: -170 },
    { id: "n2", x: 760, y: -20 },
    { id: "n3", x: 770, y: 145 },

    { id: "n4", x: 960, y: -170 },
    { id: "n5", x: 962, y: -10 },
    { id: "n6", x: 965, y: 150 },

    { id: "n7", x: 1165, y: -165 },
    { id: "n8", x: 1150, y: -5 },
    { id: "n9", x: 1132, y: 155 },

    { id: "ne1", x: 1320, y: 265 },
    { id: "ne2", x: 1495, y: 165 },
    { id: "ne3", x: 1700, y: 55 },
    { id: "ne4", x: 1920, y: -85 },

    { id: "e1", x: 1410, y: 425 },
    { id: "e2", x: 1615, y: 425 },
    { id: "e3", x: 1840, y: 425 },
    { id: "e4", x: 2080, y: 425 },
    { id: "e5", x: 2290, y: 425 },

    { id: "el1", x: 1450, y: 575 },
    { id: "el2", x: 1685, y: 575 },
    { id: "el3", x: 1930, y: 575 },
    { id: "el4", x: 2170, y: 575 },

    { id: "se1", x: 1365, y: 735 },
    { id: "se2", x: 1510, y: 845 },
    { id: "se3", x: 1660, y: 980 },
    { id: "se4", x: 1815, y: 1135 },
    { id: "se5", x: 1995, y: 1305 },

    { id: "se6", x: 1430, y: 830 },
    { id: "se7", x: 1545, y: 975 },

    { id: "s1", x: 880, y: 850 },
    { id: "s2", x: 892, y: 1010 },
    { id: "s3", x: 900, y: 1200 },
    { id: "s4", x: 905, y: 1395 },

    { id: "s5", x: 1040, y: 850 },
    { id: "s6", x: 1095, y: 1015 },
    { id: "s7", x: 1145, y: 1215 },

    { id: "sw1", x: 605, y: 770 },
    { id: "sw2", x: 485, y: 885 },
    { id: "sw3", x: 340, y: 1025 },
    { id: "sw4", x: 170, y: 1175 },
    { id: "sw5", x: -15, y: 1295 },

    { id: "o1", x: -150, y: 885 },
    { id: "o2", x: 40, y: 885 },

    { id: "o3", x: 2100, y: 760 },
    { id: "o4", x: 2330, y: 760 },

    { id: "o5", x: 1325, y: -165 },
    { id: "o6", x: 1485, y: -35 },

    { id: "o7", x: 420, y: 1360 },
    { id: "o8", x: 590, y: 1245 },
];

const routes: Route[] = [
    { id: "teal-main", color: "#22c7b8", width: 8, opacity: 0.82, stops: ["w1", "w2", "w3", "w4", "w5", "c5", "c6", "c7", "c8", "c9", "e1", "e2", "e3", "e4", "e5"] },
    { id: "blue-main", color: "#3b82f6", width: 7, opacity: 0.74, stops: ["n1", "n2", "n3", "c2", "c6", "c11", "c15", "s1", "s2", "s3", "s4"] },
    { id: "orange-main", color: "#f97316", width: 7, opacity: 0.66, stops: ["nw1", "nw2", "nw3", "nw4", "nw5", "c1", "c6", "c12", "c16", "se1", "se2", "se3", "se4", "se5"] },
    { id: "red-main", color: "#ef4444", width: 6, opacity: 0.6, stops: ["wl1", "wl2", "wl3", "c10", "c11", "c12", "c13", "el1", "el2", "el3", "el4"] },

    { id: "violet-upper", color: "#8b5cf6", width: 5, opacity: 0.55, stops: ["nw3", "c1", "c2", "c3", "c4", "ne1", "ne2", "ne3", "ne4"] },
    { id: "yellow-north-south", color: "#eab308", width: 5, opacity: 0.54, stops: ["n7", "n8", "n9", "c4", "c8", "c13", "c16", "s5", "s6", "s7"] },
    { id: "pink-lower", color: "#ec4899", width: 5, opacity: 0.5, stops: ["wl1", "wl2", "wl3", "c10", "c14", "c15", "c16", "el1", "el2", "el3"] },
    { id: "green-diagonal", color: "#22c55e", width: 5, opacity: 0.5, stops: ["sw4", "sw3", "sw2", "sw1", "c14", "c11", "c7", "c3", "ne1", "ne2"] },
    { id: "cyan-central", color: "#06b6d4", width: 4.5, opacity: 0.46, stops: ["w5", "c5", "c10", "c14", "c15", "c16", "se6", "se7"] },
    { id: "lime-core", color: "#84cc16", width: 4, opacity: 0.42, stops: ["n3", "c2", "c3", "c7", "c12", "c15", "s5"] },
    { id: "indigo-diagonal", color: "#6366f1", width: 4, opacity: 0.42, stops: ["n6", "c4", "c8", "c12", "c16", "se2"] },
    { id: "rose-express", color: "#f43f5e", width: 4, opacity: 0.4, stops: ["w3", "c5", "c7", "c9", "e3"] },
    { id: "emerald-east-south", color: "#10b981", width: 4, opacity: 0.4, stops: ["e2", "c9", "c13", "c16", "s6"] },
    { id: "sky-south-east", color: "#0ea5e9", width: 4, opacity: 0.38, stops: ["sw2", "c14", "c15", "c16", "el1", "el3"] },
    { id: "amber-northeast", color: "#f59e0b", width: 3.5, opacity: 0.36, stops: ["o5", "o6", "ne2", "c4", "c8", "c13", "se1"] },
    { id: "mint-commuter", color: "#34d399", width: 3, opacity: 0.3, stops: ["o1", "o2", "wl3", "c11", "c13", "el2", "o3", "o4"] },
    { id: "gray-outer", color: "#64748b", width: 3, opacity: 0.28, stops: ["sw5", "sw4", "c14", "c10", "c6", "ne1"] },
    { id: "light-blue-southwest", color: "#38bdf8", width: 3, opacity: 0.3, stops: ["o7", "o8", "sw1", "c14", "c11", "c7", "n3"] },
    { id: "brown-spine", color: "#a16207", width: 3.5, opacity: 0.3, stops: ["nw2", "c1", "c5", "c10", "c14", "s2"] },
    { id: "slate-cross", color: "#94a3b8", width: 3.5, opacity: 0.28, stops: ["w4", "c10", "c6", "c3", "n5"] },
];

const nodeMap = Object.fromEntries(nodes.map((node) => [node.id, node]));

function getStationUsage(routes: Route[]) {
    const usage = new Map<string, number>();

    for (const route of routes) {
        const uniqueStops = new Set(route.stops);

        for (const stopId of uniqueStops) {
            usage.set(stopId, (usage.get(stopId) ?? 0) + 1);
        }
    }

    return usage;
}

function getRoutePoints(route: Route): Point[] {
    return route.stops
        .map((stopId) => nodeMap[stopId])
        .filter((node): node is Node => Boolean(node))
        .map((node) => ({ x: node.x, y: node.y }));
}

function buildSmoothPath(points: Point[]) {
    if (points.length === 0) return "";
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
    if (points.length === 2) {
        return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
    }

    let d = `M ${points[0].x} ${points[0].y}`;

    for (let index = 0; index < points.length - 1; index++) {
        const p0 = points[index - 1] ?? points[index];
        const p1 = points[index];
        const p2 = points[index + 1];
        const p3 = points[index + 2] ?? p2;

        const cp1x = p1.x + (p2.x - p0.x) / 6;
        const cp1y = p1.y + (p2.y - p0.y) / 6;

        const cp2x = p2.x - (p3.x - p1.x) / 6;
        const cp2y = p2.y - (p3.y - p1.y) / 6;

        d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
    }

    return d;
}

export function TransitBackground() {
    const stationUsage = getStationUsage(routes);

    return (
        <Box
            position="fixed"
            inset="0"
            overflow="hidden"
            pointerEvents="none"
            zIndex="0"
            opacity="0.12"
            filter="blur(0.2px)"
        >
            <svg
                width="100%"
                height="100%"
                viewBox="120 40 1750 1120"
                preserveAspectRatio="xMidYMid slice"
            >
                <defs>
                    <radialGradient id="downtownGlow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.10" />
                        <stop offset="45%" stopColor="#22c7b8" stopOpacity="0.05" />
                        <stop offset="100%" stopColor="#22c7b8" stopOpacity="0" />
                    </radialGradient>
                </defs>

                {/* subtle downtown glow */}
                <ellipse
                    cx="920"
                    cy="500"
                    rx="420"
                    ry="270"
                    fill="url(#downtownGlow)"
                />

                {/* routes */}
                {routes.map((route) => {
                    const points = getRoutePoints(route);
                    const pathD = buildSmoothPath(points);

                    return (
                        <path
                            key={route.id}
                            d={pathD}
                            fill="none"
                            stroke={route.color}
                            strokeWidth={route.width}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            opacity={route.opacity ?? 1}
                        />
                    );
                })}

                {/* stations */}
                {nodes.map((node) => {
                    const routeCount = stationUsage.get(node.id) ?? 0;

                    const radius =
                        routeCount >= 6 ? 15 :
                            routeCount >= 4 ? 12 :
                                routeCount >= 3 ? 9 :
                                    routeCount >= 2 ? 7 : 5;

                    const strokeWidth =
                        routeCount >= 4 ? 4 :
                            routeCount >= 2 ? 3 : 2;

                    const stroke =
                        routeCount >= 5 ? "#f8fafc" :
                            routeCount >= 3 ? "#cbd5e1" :
                                "#718096";

                    return (
                        <circle
                            key={node.id}
                            cx={node.x}
                            cy={node.y}
                            r={radius}
                            fill="#050d20"
                            stroke={stroke}
                            strokeWidth={strokeWidth}
                            opacity={routeCount >= 3 ? 0.95 : 0.62}
                        />
                    );
                })}
            </svg>
        </Box>
    );
}