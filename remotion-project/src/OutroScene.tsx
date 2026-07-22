import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
} from "remotion";
import React from "react";

export const OutroScene: React.FC<{
  summary: string;
  ctaText: string;
}> = ({ summary, ctaText }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const labelOpacity = interpolate(frame, [0, 16], [0, 1], {
    extrapolateRight: "clamp",
  });

  const summaryOpacity = interpolate(frame, [12, 32], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const summaryY = interpolate(frame, [12, 32], [20, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const lineWidth = interpolate(frame, [38, 60], [0, 180], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const ctaSpring = spring({
    frame: frame - 55,
    fps,
    from: 0,
    to: 1,
    config: { damping: 12, stiffness: 120, mass: 0.7 },
  });
  const ctaScale = interpolate(ctaSpring, [0, 1], [0.6, 1]);
  const ctaOpacity = interpolate(frame, [55, 72], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const pulse =
    1 + Math.sin((frame - 70) / 10) * 0.025 * (frame > 70 ? 1 : 0);

  const iconsOpacity = interpolate(frame, [80, 100], [0, 1], {
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
        padding: "0 100px",
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
          opacity: labelOpacity,
          fontSize: 20,
          color: "#06b6d4",
          fontFamily: "sans-serif",
          letterSpacing: "3px",
          textTransform: "uppercase",
          fontWeight: 600,
          marginBottom: 20,
        }}
      >
        Quick Recap
      </div>

      <div
        style={{
          opacity: summaryOpacity,
          transform: `translateY(${summaryY}px)`,
          fontSize: 36,
          fontWeight: 700,
          color: "#ffffff",
          fontFamily: "sans-serif",
          textAlign: "center",
          lineHeight: 1.45,
          maxWidth: 900,
          letterSpacing: "-0.5px",
        }}
      >
        {summary}
      </div>

      <div
        style={{
          width: lineWidth,
          height: 4,
          borderRadius: 2,
          background: "linear-gradient(90deg, #6366f1, #06b6d4)",
          margin: "32px 0",
        }}
      />

      <div
        style={{
          opacity: ctaOpacity,
          transform: `scale(${ctaScale * pulse})`,
          background: "linear-gradient(135deg, #6366f1, #06b6d4)",
          borderRadius: 50,
          padding: "18px 48px",
          boxShadow: "0 16px 40px rgba(99,102,241,0.4)",
        }}
      >
        <div
          style={{
            fontSize: 26,
            fontWeight: 800,
            color: "#ffffff",
            fontFamily: "sans-serif",
            letterSpacing: "0.5px",
          }}
        >
          {ctaText}
        </div>
      </div>

      <div
        style={{
          opacity: iconsOpacity,
          display: "flex",
          gap: 36,
          marginTop: 36,
        }}
      >
        <div style={{ fontSize: 18, color: "#94a3b8", fontFamily: "sans-serif", display: "flex", alignItems: "center", gap: 8 }}>🔔 Subscribe</div>
        <div style={{ fontSize: 18, color: "#94a3b8", fontFamily: "sans-serif", display: "flex", alignItems: "center", gap: 8 }}>❤️ Like</div>
        <div style={{ fontSize: 18, color: "#94a3b8", fontFamily: "sans-serif", display: "flex", alignItems: "center", gap: 8 }}>🔗 Share</div>
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