import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";

export const StatsScene: React.FC<{
  label: string;
  number: number;
  suffix: string;
  description: string;
}> = ({ label, number, suffix, description }) => {
  const frame = useCurrentFrame();
  const { } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const labelOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateRight: "clamp",
  });

  const countProgress = interpolate(frame, [15, 75], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const currentNumber = Math.round(number * countProgress);
  const formattedNumber = currentNumber.toLocaleString("en-IN");

  const numberScale = interpolate(frame, [15, 20], [0.85, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const descOpacity = interpolate(frame, [75, 95], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const descY = interpolate(frame, [75, 95], [20, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const ringScale = interpolate(frame, [15, 75], [0.9, 1.15], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const ringOpacity = interpolate(frame, [15, 30, 75], [0, 0.25, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
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
            "radial-gradient(circle, rgba(99,102,241,0.35) 0%, transparent 70%)",
          transform: `scale(${ringScale})`,
          opacity: ringOpacity,
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          opacity: labelOpacity,
          fontSize: 22,
          color: "#06b6d4",
          fontFamily: "sans-serif",
          letterSpacing: "3px",
          textTransform: "uppercase",
          fontWeight: 600,
          marginBottom: 20,
        }}
      >
        {label}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          transform: `scale(${numberScale})`,
        }}
      >
        <div
          style={{
            fontSize: 130,
            fontWeight: 900,
            background: "linear-gradient(135deg, #818cf8, #22d3ee)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            fontFamily: "sans-serif",
            letterSpacing: "-3px",
            lineHeight: 1,
          }}
        >
          {formattedNumber}
        </div>
        <div
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#22d3ee",
            fontFamily: "sans-serif",
          }}
        >
          {suffix}
        </div>
      </div>

      <div
        style={{
          opacity: descOpacity,
          transform: `translateY(${descY}px)`,
          fontSize: 26,
          color: "#94a3b8",
          fontFamily: "sans-serif",
          textAlign: "center",
          maxWidth: 650,
          marginTop: 28,
          lineHeight: 1.5,
          padding: "0 40px",
        }}
      >
        {description}
      </div>

      <div
        style={{
          opacity: labelOpacity,
          position: "absolute",
          bottom: 30,
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