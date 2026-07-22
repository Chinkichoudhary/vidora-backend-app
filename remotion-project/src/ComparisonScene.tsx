import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
} from "remotion";
import React from "react";

export const ComparisonScene: React.FC<{
  heading: string;
  leftTitle: string;
  leftPoints: string[];
  rightTitle: string;
  rightPoints: string[];
}> = ({ heading, leftTitle, leftPoints, rightTitle, rightPoints }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Background fade in / out ──────────────────────────────────
  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  




  // ── Heading ──────────────────────────────────────────────────
  const headingOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateRight: "clamp",
  });
  const headingY = interpolate(frame, [0, 18], [25, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  // ── Left card slides in from left ───────────────────────────────
  const leftSpring = spring({
    frame: frame - 15,
    fps,
    from: 0,
    to: 1,
    config: { damping: 14, stiffness: 110, mass: 0.7 },
  });
  const leftX = interpolate(leftSpring, [0, 1], [-200, 0]);
  const leftOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // ── Right card slides in from right ─────────────────────────────
  const rightSpring = spring({
    frame: frame - 15,
    fps,
    from: 0,
    to: 1,
    config: { damping: 14, stiffness: 110, mass: 0.7 },
  });
  const rightX = interpolate(rightSpring, [0, 1], [200, 0]);
  const rightOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // ── "VS" badge pops in last ─────────────────────────────────────
  const vsScale = interpolate(frame, [40, 50, 58], [0, 1.3, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const vsOpacity = interpolate(frame, [40, 50], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // ── Helper to stagger bullet points within each column ──────────
  const renderPoints = (pts: string[], baseDelay: number) =>
    pts.map((pt, i) => {
      const startFrame = baseDelay + i * 15;
      const opacity = interpolate(
        frame,
        [startFrame, startFrame + 12],
        [0, 1],
        { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
      );
      const y = interpolate(frame, [startFrame, startFrame + 12], [12, 0], {
        extrapolateRight: "clamp",
        extrapolateLeft: "clamp",
      });
      return (
        <div
          key={i}
          style={{
            opacity,
            transform: `translateY(${y}px)`,
            fontSize: 21,
            color: "#cbd5e1",
            fontFamily: "sans-serif",
            lineHeight: 1.5,
            marginBottom: 14,
            display: "flex",
            gap: 10,
          }}
        >
          <span style={{ color: "#06b6d4" }}>•</span>
          <span>{pt}</span>
        </div>
      );
    });

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "flex-start",
        alignItems: "center",
        flexDirection: "column",
        padding: "60px 80px",
        overflow: "hidden",
      }}
    >
      {/* ── Heading ── */}
      <div
        style={{
          opacity: headingOpacity,
          transform: `translateY(${headingY}px)`,
          fontSize: 42,
          fontWeight: 800,
          color: "#ffffff",
          fontFamily: "sans-serif",
          textAlign: "center",
          marginBottom: 40,
          letterSpacing: "-1px",
        }}
      >
        {heading}
      </div>

      {/* ── Two Columns Row ── */}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          gap: 0,
          width: "100%",
          justifyContent: "center",
          alignItems: "flex-start",
          position: "relative",
        }}
      >
        {/* LEFT CARD */}
        <div
          style={{
            opacity: leftOpacity,
            transform: `translateX(${leftX}px)`,
            background: "rgba(99,102,241,0.12)",
            border: "2px solid rgba(99,102,241,0.4)",
            borderRadius: 20,
            padding: "32px 36px",
            width: 440,
            minHeight: 260,
          }}
        >
          <div
            style={{
              fontSize: 26,
              fontWeight: 800,
              color: "#818cf8",
              fontFamily: "sans-serif",
              marginBottom: 18,
            }}
          >
            {leftTitle}
          </div>
          {renderPoints(leftPoints, 35)}
        </div>

        {/* VS BADGE */}
        <div
          style={{
            opacity: vsOpacity,
            transform: `scale(${vsScale})`,
            position: "absolute",
            left: "50%",
            top: 90,
            marginLeft: -38,
            width: 76,
            height: 76,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #6366f1, #06b6d4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 10px 30px rgba(99,102,241,0.5)",
            zIndex: 10,
          }}
        >
          <span
            style={{
              color: "#ffffff",
              fontSize: 24,
              fontWeight: 800,
              fontFamily: "sans-serif",
            }}
          >
            VS
          </span>
        </div>

        {/* RIGHT CARD */}
        <div
          style={{
            opacity: rightOpacity,
            transform: `translateX(${rightX}px)`,
            background: "rgba(6,182,212,0.10)",
            border: "2px solid rgba(6,182,212,0.4)",
            borderRadius: 20,
            padding: "32px 36px",
            width: 440,
            minHeight: 260,
          }}
        >
          <div
            style={{
              fontSize: 26,
              fontWeight: 800,
              color: "#22d3ee",
              fontFamily: "sans-serif",
              marginBottom: 18,
            }}
          >
            {rightTitle}
          </div>
          {renderPoints(rightPoints, 35)}
        </div>
      </div>

      {/* Brand tag */}
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