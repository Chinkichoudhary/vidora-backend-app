import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
} from "remotion";
import React from "react";

export const BulletScene: React.FC<{
  heading: string;
  points: string[];
}> = ({ heading, points }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const headingOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const headingY = interpolate(frame, [0, 20], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const STAGGER = 25;
  const START_DELAY = 30;

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "center",
        alignItems: "flex-start",
        flexDirection: "column",
        padding: "0 110px",
        gap: 0,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
          pointerEvents: "none",
          right: -100,
          top: -100,
        }}
      />

      <div
        style={{
          opacity: headingOpacity,
          transform: `translateY(${headingY}px)`,
          fontSize: 48,
          fontWeight: 800,
          color: "#ffffff",
          fontFamily: "sans-serif",
          marginBottom: 50,
          letterSpacing: "-1px",
        }}
      >
        {heading}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {points.map((point, index) => {
          const startFrame = START_DELAY + index * STAGGER;

          const pointSpring = spring({
            frame: frame - startFrame,
            fps,
            from: 0,
            to: 1,
            config: { damping: 14, stiffness: 110, mass: 0.6 },
          });

          const pointX = interpolate(pointSpring, [0, 1], [-60, 0]);
          const pointOpacity = interpolate(
            frame,
            [startFrame, startFrame + 15],
            [0, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          const circleScale = interpolate(
            frame,
            [startFrame, startFrame + 10, startFrame + 18],
            [0, 1.2, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          return (
            <div
              key={index}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 24,
                opacity: pointOpacity,
                transform: `translateX(${pointX}px)`,
              }}
            >
              <div
                style={{
                  flexShrink: 0,
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background:
                    "linear-gradient(135deg, #6366f1, #06b6d4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transform: `scale(${circleScale})`,
                  boxShadow: "0 8px 24px rgba(99,102,241,0.4)",
                }}
              >
                <span
                  style={{
                    color: "#ffffff",
                    fontSize: 22,
                    fontWeight: 800,
                    fontFamily: "sans-serif",
                  }}
                >
                  {index + 1}
                </span>
              </div>

              <div
                style={{
                  fontSize: 30,
                  fontWeight: 500,
                  color: "#e2e8f0",
                  fontFamily: "sans-serif",
                  lineHeight: 1.4,
                  maxWidth: 750,
                }}
              >
                {point}
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          opacity: headingOpacity,
          position: "absolute",
          bottom: 30,
          right: 60,
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