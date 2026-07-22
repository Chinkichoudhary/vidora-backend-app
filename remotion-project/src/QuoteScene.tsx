import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";

export const QuoteScene: React.FC<{
  quote: string;
  attribution: string;
}> = ({ quote, attribution }) => {
  const frame = useCurrentFrame();
  const { } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const markScale = interpolate(frame, [0, 14, 22], [0, 1.3, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const markOpacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateRight: "clamp",
  });

  const quoteOpacity = interpolate(frame, [20, 45], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });
  const quoteY = interpolate(frame, [20, 45], [25, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const lineWidth = interpolate(frame, [50, 75], [0, 140], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const attrOpacity = interpolate(frame, [65, 85], [0, 1], {
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
        gap: 0,
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
            "radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          opacity: markOpacity,
          transform: `scale(${markScale})`,
          fontSize: 90,
          fontWeight: 900,
          color: "#6366f1",
          fontFamily: "Georgia, serif",
          lineHeight: 0.5,
          marginBottom: 20,
        }}
      >
        "
      </div>

      <div
        style={{
          opacity: quoteOpacity,
          transform: `translateY(${quoteY}px)`,
          fontSize: 44,
          fontWeight: 700,
          color: "#ffffff",
          fontFamily: "sans-serif",
          textAlign: "center",
          lineHeight: 1.4,
          maxWidth: 950,
          letterSpacing: "-0.5px",
        }}
      >
        {quote}
      </div>

      <div
        style={{
          width: lineWidth,
          height: 4,
          borderRadius: 2,
          background: "linear-gradient(90deg, #6366f1, #06b6d4)",
          margin: "28px 0",
        }}
      />

      <div
        style={{
          opacity: attrOpacity,
          fontSize: 20,
          color: "#94a3b8",
          fontFamily: "sans-serif",
          letterSpacing: "2px",
          textTransform: "uppercase",
          fontWeight: 600,
        }}
      >
        {attribution}
      </div>

      <div
        style={{
          opacity: attrOpacity,
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