import { Box } from '@mui/material'

function Leaf({ x, y, size = 1, angle = 0, color = '#4a7c59', opacity = 0.35 }) {
  const s = size
  return (
    <g transform={`translate(${x}, ${y}) rotate(${angle})`}>
      <path
        d={`M 0,${4 * s} C ${-10 * s},${-5 * s} ${-9 * s},${-22 * s} 0,${-30 * s} C ${9 * s},${-22 * s} ${10 * s},${-5 * s} 0,${4 * s} Z`}
        fill={color}
        opacity={opacity}
      />
      <line x1="0" y1={4 * s} x2="0" y2={-30 * s} stroke={color} strokeWidth={0.8 * s} opacity={opacity * 0.7} />
    </g>
  )
}

export default function BotanicalBanner() {
  return (
    <Box sx={{ width: '100%', overflow: 'hidden', lineHeight: 0, flexShrink: 0 }}>
      <svg
        viewBox="0 0 1440 88"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
        style={{ width: '100%', height: '88px', display: 'block' }}
      >
        {/* Subtle background tint */}
        <rect width="1440" height="88" fill="#4a7c59" opacity="0.06" />

        {/* Wave layers, back to front */}
        <path
          d="M0,42 C180,18 360,62 540,42 C720,22 900,58 1080,38 C1240,20 1360,48 1440,36 L1440,88 L0,88 Z"
          fill="#4a7c59" opacity="0.10"
        />
        <path
          d="M0,56 C220,36 420,72 640,54 C860,36 1060,68 1260,50 C1360,42 1410,58 1440,52 L1440,88 L0,88 Z"
          fill="#4a7c59" opacity="0.16"
        />
        <path
          d="M0,70 C260,54 480,82 720,67 C960,52 1160,76 1380,62 C1410,60 1428,67 1440,64 L1440,88 L0,88 Z"
          fill="#4a7c59" opacity="0.28"
        />

        {/* Leaves — left cluster */}
        <Leaf x={55}  y={58} size={0.95} angle={-30} opacity={0.32} />
        <Leaf x={80}  y={52} size={0.75} angle={8}   opacity={0.22} />
        <Leaf x={38}  y={62} size={0.65} angle={-55} opacity={0.18} color="#5c8a70" />

        {/* Leaves — right cluster */}
        <Leaf x={1385} y={55} size={0.90} angle={28}  opacity={0.30} />
        <Leaf x={1360} y={62} size={0.70} angle={-10} opacity={0.20} />
        <Leaf x={1405} y={60} size={0.60} angle={55}  opacity={0.16} color="#5c8a70" />

        {/* Scattered leaves — mid */}
        <Leaf x={380}  y={50} size={0.65} angle={15}  opacity={0.18} color="#4e7da3" />
        <Leaf x={720}  y={44} size={0.55} angle={-20} opacity={0.15} />
        <Leaf x={1060} y={48} size={0.60} angle={10}  opacity={0.16} color="#4e7da3" />

        {/* Small accent dots */}
        <circle cx="160"  cy="28" r="2.5" fill="#4a7c59" opacity="0.18" />
        <circle cx="310"  cy="18" r="2"   fill="#4a7c59" opacity="0.13" />
        <circle cx="900"  cy="22" r="2.5" fill="#4e7da3" opacity="0.17" />
        <circle cx="1130" cy="16" r="2"   fill="#4a7c59" opacity="0.13" />
        <circle cx="560"  cy="32" r="1.8" fill="#4e7da3" opacity="0.14" />
      </svg>
    </Box>
  )
}
