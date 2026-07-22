import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  spring,
} from "remotion";
import React from "react";

export const DefinitionScene: React.FC<{
  term: string;
  explanation: string;
}> = ({ term, explanation }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const termSpring = spring({
    frame,
    fps,
    from: 0,
    to: 1,
    config: { damping: 14, stiffness: 110, mass: 0.7 },
  });
  const termX = interpolate(termSpring, [0, 1], [-150, 0]);
  const termOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const cardScale = interpolate(frame, [0, 20], [0.8, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const explanationSpring = spring({
    frame: frame - 20,
    fps,
    from: 0,
    to: 1,
    config: { damping: 14, stiffness: 110, mass: 0.7 },
  });
  const explanationX = interpolate(explanationSpring, [0, 1], [150, 0]);
  const explanationOpacity = interpolate(frame, [20, 45], [0, 1], {
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [35, 60], [0, 100], {
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
        flexDirection: "row",
        padding: "0 80px",
        gap: 40,
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
        }}
      />

      <div
        style={{
          flex: "0 0 38%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            opacity: termOpacity,
            transform: `translateX(${termX}px) scale(${cardScale})`,
            background: "linear-gradient(135deg, #6366f1, #4338ca)",
            borderRadius: 24,
            padding: "40px 36px",
            boxShadow: "0 20px 60px rgba(99,102,241,0.35)",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 16,
              color: "rgba(255,255,255,0.7)",
              fontFamily: "sans-serif",
              letterSpacing: "2px",
              textTransform: "uppercase",
              marginBottom: 12,
              fontWeight: 600,
            }}
          >
            Term
          </div>
          <div
            style={{
              fontSize: 48,
              fontWeight: 800,
              color: "#ffffff",
              fontFamily: "sans-serif",
              lineHeight: 1.2,
            }}
          >
            {term}
          </div>
        </div>
      </div>

      <div
        style={{
          flex: "0 0 auto",
          width: lineWidth,
          height: 3,
          background: "linear-gradient(90deg, #6366f1, #06b6d4)",
          borderRadius: 2,
        }}
      />

      <div
        style={{
          flex: "1",
          display: "flex",
          justifyContent: "flex-start",
          alignItems: "center",
        }}
      >
        <div
          style={{
            opacity: explanationOpacity,
            transform: `translateX(${explanationX}px)`,
          }}
        >
          <div
            style={{
              fontSize: 16,
              color: "#06b6d4",
              fontFamily: "sans-serif",
              letterSpacing: "2px",
              textTransform: "uppercase",
              marginBottom: 14,
              fontWeight: 600,
            }}
          >
            Means
          </div>
          <div
            style={{
              fontSize: 32,
              fontWeight: 500,
              color: "#e2e8f0",
              fontFamily: "sans-serif",
              lineHeight: 1.5,
              maxWidth: 480,
            }}
          >
            {explanation}
          </div>
        </div>
      </div>

      <div
        style={{
          opacity: explanationOpacity,
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