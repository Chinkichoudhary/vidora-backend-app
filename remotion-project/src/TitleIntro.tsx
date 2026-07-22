import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
} from "remotion";
import React from "react";

export const TitleIntro: React.FC<{ topic: string }> = ({ topic }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const topicSpring = spring({
    frame,
    fps,
    from: 0,
    to: 1,
    config: {
      damping: 12,
      stiffness: 100,
      mass: 0.8,
    },
  });

  const topicScale = interpolate(topicSpring, [0, 1], [0.7, 1]);
  const topicOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [25, 55], [0, 260], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
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
        gap: 24,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          opacity: topicOpacity,
          fontSize: 20,
          color: "#06b6d4",
          fontFamily: "sans-serif",
          letterSpacing: "3px",
          textTransform: "uppercase",
          fontWeight: 600,
        }}
      >
        Today's Topic
      </div>

      <div
        style={{
          opacity: topicOpacity,
          transform: `scale(${topicScale})`,
          fontSize: 76,
          fontWeight: 800,
          color: "#ffffff",
          textAlign: "center",
          fontFamily: "sans-serif",
          letterSpacing: "-2px",
          lineHeight: 1.15,
          maxWidth: 950,
          padding: "0 40px",
        }}
      >
        {topic}
      </div>

      <div
        style={{
          width: lineWidth,
          height: 5,
          borderRadius: 3,
          background: "linear-gradient(90deg, #6366f1, #06b6d4)",
        }}
      />

      <div
        style={{
          opacity: topicOpacity,
          position: "absolute",
          bottom: 36,
          fontSize: 18,
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