import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";
import * as Icons from "lucide-react";

export const IconGridScene: React.FC<{
  heading: string;
  description: string;
  iconNames: string[];
}> = ({ heading, description, iconNames }) => {
  const frame = useCurrentFrame();
  const { } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const headingOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateRight: "clamp",
  });
  const headingY = interpolate(frame, [0, 18], [25, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const descOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const descY = interpolate(frame, [15, 35], [15, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const START_DELAY = 40;
  const STAGGER = 12;
  const cols = 3;

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "flex-start",
        alignItems: "center",
        flexDirection: "column",
        padding: "60px 60px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          opacity: headingOpacity,
          transform: `translateY(${headingY}px)`,
          fontSize: 40,
          fontWeight: 800,
          color: "#ffffff",
          fontFamily: "sans-serif",
          textAlign: "center",
          marginBottom: 16,
          letterSpacing: "-1px",
        }}
      >
        {heading}
      </div>

      <div
        style={{
          opacity: descOpacity,
          transform: `translateY(${descY}px)`,
          fontSize: 20,
          color: "#94a3b8",
          fontFamily: "sans-serif",
          textAlign: "center",
          maxWidth: 750,
          lineHeight: 1.5,
          marginBottom: 50,
        }}
      >
        {description}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 28,
        }}
      >
        {iconNames.map((iconName, index) => {
          const startFrame = START_DELAY + index * STAGGER;

          const scale = interpolate(
            frame,
            [startFrame, startFrame + 12, startFrame + 20],
            [0, 1.15, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );
          const opacity = interpolate(
            frame,
            [startFrame, startFrame + 14],
            [0, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          const IconComponent =
            (Icons as any)[iconName] || Icons.Circle;

          return (
            <div
              key={index}
              style={{
                opacity,
                transform: `scale(${scale})`,
                width: 150,
                height: 150,
                background: "rgba(99,102,241,0.12)",
                border: "2px solid rgba(99,102,241,0.35)",
                borderRadius: 20,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 12px 30px rgba(99,102,241,0.2)",
              }}
            >
              <IconComponent size={56} color="#22d3ee" strokeWidth={1.6} />
            </div>
          );
        })}
      </div>

      <div
        style={{
          opacity: headingOpacity,
          position: "absolute",
          bottom: 24,
          fontSize: 16,
          color: "#475569",
          fontFamily: "sans-serif",
          letterSpacing: "2px",
          textTransform: "uppercase",
        }}
      >
        Vidora • Learn Visually
      </div>
    </AbsoluteFill>
  );
};