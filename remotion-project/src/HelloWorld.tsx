import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";

export const TitleScene: React.FC<{ title: string; subtitle: string }> = ({
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // ── Fade in / out ──────────────────────────────────────────
  const fadeIn = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.ease,
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 30, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", easing: Easing.ease }
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // ── Title slides up ─────────────────────────────────────────
  const titleY = interpolate(frame, [0, 30], [50, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  // ── Underline grows ─────────────────────────────────────────
  const lineWidth = interpolate(frame, [30, 65], [0, 220], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  // ── Subtitle fades in ────────────────────────────────────────
  const subtitleOpacity = interpolate(frame, [50, 80], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.ease,
  });
  const subtitleY = interpolate(frame, [50, 80], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  // ── Icon bounces in ──────────────────────────────────────────
  const iconScale = interpolate(frame, [70, 90, 100], [0, 1.3, 1.0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
  const iconOpacity = interpolate(frame, [70, 85], [0, 1], {
    extrapolateRight: "clamp",
  });

  // ── Floating dots (decorative background) ───────────────────
  const dot1X = interpolate(frame, [0, durationInFrames], [0, 30], {
    extrapolateRight: "clamp",
  });
  const dot2X = interpolate(frame, [0, durationInFrames], [0, -20], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 20,
        overflow: "hidden",
      }}
    >
      {/* ── Decorative background blobs ── */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 100 + dot1X,
          width: 300,
          height: 300,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 60,
          right: 120 + dot2X,
          width: 250,
          height: 250,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(6,182,212,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      {/* ── Icon ── */}
      <div
        style={{
          opacity: iconOpacity,
          transform: `scale(${iconScale})`,
          fontSize: 72,
          marginBottom: 8,
        }}
      >
        🧠
      </div>

      {/* ── Main Title ── */}
      <div
        style={{
          opacity,
          transform: `translateY(${titleY}px)`,
          fontSize: 68,
          fontWeight: 800,
          color: "#ffffff",
          textAlign: "center",
          fontFamily: "sans-serif",
          letterSpacing: "-1.5px",
          lineHeight: 1.15,
          maxWidth: 900,
          padding: "0 40px",
        }}
      >
        {title}
      </div>

      {/* ── Animated underline bar ── */}
      <div
        style={{
          opacity,
          width: lineWidth,
          height: 5,
          borderRadius: 3,
          background: "linear-gradient(90deg, #6366f1, #06b6d4)",
        }}
      />

      {/* ── Subtitle ── */}
      <div
        style={{
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          fontSize: 26,
          color: "#94a3b8",
          fontFamily: "sans-serif",
          textAlign: "center",
          maxWidth: 700,
          padding: "0 40px",
          lineHeight: 1.6,
        }}
      >
        {subtitle}
      </div>

      {/* ── Bottom tag line ── */}
      <div
        style={{
          opacity: subtitleOpacity,
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