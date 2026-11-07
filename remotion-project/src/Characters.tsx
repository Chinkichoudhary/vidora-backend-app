import React from "react";
import { useCurrentFrame } from "remotion";

const Svg: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg viewBox="0 0 200 240" width="100%" height="100%">
    {children}
  </svg>
);

const Robot: React.FC<{ f: number }> = ({ f }) => {
  const bounce = Math.sin(f / 8) * 6;
  const arm = -150 + Math.sin(f / 5) * 18;
  const eye = f % 90 < 4 ? 1 : 9;
  const glow = 0.6 + 0.4 * Math.sin(f / 6);
  return (
    <Svg>
      <g transform={`translate(0 ${bounce})`}>
        <line x1="100" y1="24" x2="100" y2="44" stroke="#94a3b8" strokeWidth="4" />
        <circle cx="100" cy="18" r="9" fill="#f472b6" opacity={glow} />
        <rect x="55" y="44" width="90" height="70" rx="20" fill="#6366f1" />
        <rect x="66" y="58" width="68" height="40" rx="12" fill="#0f172a" />
        <ellipse cx="85" cy="78" rx="8" ry={eye} fill="#06b6d4" />
        <ellipse cx="115" cy="78" rx="8" ry={eye} fill="#06b6d4" />
        <rect x="70" y="118" width="60" height="68" rx="16" fill="#4f46e5" />
        <circle cx="100" cy="150" r="9" fill="#06b6d4" opacity={glow} />
        <rect x="50" y="122" width="14" height="48" rx="7" fill="#818cf8" />
        <g transform={`rotate(${arm} 143 126)`}>
          <rect x="136" y="122" width="14" height="48" rx="7" fill="#818cf8" />
        </g>
        <rect x="78" y="188" width="18" height="14" rx="5" fill="#312e81" />
        <rect x="104" y="188" width="18" height="14" rx="5" fill="#312e81" />
      </g>
    </Svg>
  );
};

const Bulb: React.FC<{ f: number }> = ({ f }) => {
  const bob = Math.sin(f / 10) * 7;
  const pulse = 0.55 + 0.45 * Math.sin(f / 6);
  return (
    <Svg>
      <g transform={`translate(0 ${bob})`}>
        {[-120, -80, -40, 0, 40, 80, 120].map((a) => (
          <line
            key={a}
            x1="100" y1="22" x2="100" y2="4"
            stroke="#fde047" strokeWidth="6" strokeLinecap="round"
            opacity={pulse}
            transform={`rotate(${a} 100 100)`}
          />
        ))}
        <circle cx="100" cy="100" r="50" fill="#fde047" />
        <circle cx="100" cy="100" r="36" fill="#fef9c3" opacity={pulse * 0.6} />
        <circle cx="84" cy="98" r="5" fill="#0f172a" />
        <circle cx="116" cy="98" r="5" fill="#0f172a" />
        <path d="M82 118 Q100 134 118 118" stroke="#0f172a" strokeWidth="5" fill="none" strokeLinecap="round" />
        <rect x="78" y="146" width="44" height="14" rx="4" fill="#94a3b8" />
        <rect x="82" y="162" width="36" height="12" rx="4" fill="#64748b" />
      </g>
    </Svg>
  );
};

const Rocket: React.FC<{ f: number }> = ({ f }) => {
  const float = Math.sin(f / 9) * 8;
  const sway = Math.sin(f / 14) * 4;
  const flame = 1 + 0.25 * Math.sin(f * 1.1);
  return (
    <Svg>
      {[[30, 40], [170, 70], [160, 200], [40, 190]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill="#fde047" opacity={0.3 + 0.7 * Math.abs(Math.sin(f / 12 + i))} />
      ))}
      <g transform={`translate(0 ${float}) rotate(${sway} 100 120)`}>
        <path d="M100 20 C140 60 140 130 128 170 L72 170 C60 130 60 60 100 20 Z" fill="#e2e8f0" />
        <path d="M100 20 C112 32 120 44 124 56 L76 56 C80 44 88 32 100 20 Z" fill="#6366f1" />
        <circle cx="100" cy="94" r="17" fill="#06b6d4" stroke="#6366f1" strokeWidth="6" />
        <path d="M72 140 L44 178 L74 170 Z" fill="#ec4899" />
        <path d="M128 140 L156 178 L126 170 Z" fill="#ec4899" />
        <g transform={`translate(100 172) scale(1 ${flame})`}>
          <path d="M-16 0 Q0 60 16 0 Z" fill="#f59e0b" />
          <path d="M-9 0 Q0 38 9 0 Z" fill="#fde047" />
        </g>
      </g>
    </Svg>
  );
};

const Owl: React.FC<{ f: number }> = ({ f }) => {
  const bob = Math.sin(f / 12) * 5;
  const flap = Math.sin(f / 6) * 10;
  const pupil = f % 100 < 4 ? 1 : 9;
  const look = Math.sin(f / 25) * 4;
  return (
    <Svg>
      <g transform={`translate(0 ${bob})`}>
        <g transform={`rotate(${-flap} 52 130)`}>
          <ellipse cx="46" cy="140" rx="18" ry="42" fill="#92400e" />
        </g>
        <g transform={`rotate(${flap} 148 130)`}>
          <ellipse cx="154" cy="140" rx="18" ry="42" fill="#92400e" />
        </g>
        <ellipse cx="100" cy="135" rx="56" ry="64" fill="#b45309" />
        <ellipse cx="100" cy="152" rx="34" ry="44" fill="#fde68a" />
        <circle cx="78" cy="100" r="20" fill="#ffffff" />
        <circle cx="122" cy="100" r="20" fill="#ffffff" />
        <ellipse cx={78 + look} cy="100" rx="9" ry={pupil} fill="#0f172a" />
        <ellipse cx={122 + look} cy="100" rx="9" ry={pupil} fill="#0f172a" />
        <path d="M92 112 L108 112 L100 128 Z" fill="#f59e0b" />
        <ellipse cx="84" cy="200" rx="14" ry="6" fill="#f59e0b" />
        <ellipse cx="116" cy="200" rx="14" ry="6" fill="#f59e0b" />
        <polygon points="100,38 150,58 100,78 50,58" fill="#1e1b4b" />
        <rect x="78" y="64" width="44" height="14" fill="#312e81" />
        <line x1="150" y1="58" x2="150" y2="84" stroke="#fde047" strokeWidth="4" />
        <circle cx="150" cy="88" r="5" fill="#fde047" />
      </g>
    </Svg>
  );
};

export const Character: React.FC<{ name: string }> = ({ name }) => {
  const frame = useCurrentFrame();
  switch (name) {
    case "robot":
      return <Robot f={frame} />;
    case "bulb":
      return <Bulb f={frame} />;
    case "rocket":
      return <Rocket f={frame} />;
    case "owl":
      return <Owl f={frame} />;
    default:
      return null;
  }
};