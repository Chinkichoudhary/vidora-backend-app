import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";

export const TimelineScene: React.FC<{
  heading: string;
  events: { year: string; label: string }[];
}> = ({ heading, events }) => {
  const frame = useCurrentFrame();
  const { } = useVideoConfig();

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

  // ── The horizontal line grows first ─────────────────────────────
  const lineWidth = interpolate(frame, [25, 60], [0, 1100], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  // Timing: each event dot + label appears in sequence after the line
  const START_DELAY = 40;
  const STAGGER = 30;

  const itemWidth = 1100 / events.length;

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        padding: "70px 60px",
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
          marginBottom: 90,
          letterSpacing: "-1px",
        }}
      >
        {heading}
      </div>

      {/* ── Timeline row ── */}
      <div
        style={{
          position: "relative",
          width: 1100,
          height: 200,
        }}
      >
        {/* Base horizontal line */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: lineWidth,
            height: 4,
            borderRadius: 2,
            background: "linear-gradient(90deg, #6366f1, #06b6d4)",
          }}
        />

        {events.map((event, index) => {
          const startFrame = START_DELAY + index * STAGGER;

          const dotScale = interpolate(
            frame,
            [startFrame, startFrame + 10, startFrame + 16],
            [0, 1.4, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );
          const textOpacity = interpolate(
            frame,
            [startFrame + 4, startFrame + 20],
            [0, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );
          const textY = interpolate(
            frame,
            [startFrame + 4, startFrame + 20],
            [15, 0],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          const left = index * itemWidth;
          // Alternate labels above/below the line for readability
          const isAbove = index % 2 === 0;

          return (
            <div
              key={index}
              style={{
                position: "absolute",
                left,
                top: 0,
                width: itemWidth,
                display: "flex",
                justifyContent: "center",
              }}
            >
              {/* Dot on the line */}
              <div
                style={{
                  position: "absolute",
                  top: -10,
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background:
                    "linear-gradient(135deg, #6366f1, #06b6d4)",
                  transform: `scale(${dotScale})`,
                  boxShadow: "0 0 0 6px rgba(99,102,241,0.18)",
                }}
              />

              {/* Label - alternates above/below */}
              <div
                style={{
                  position: "absolute",
                  top: isAbove ? -130 : 50,
                  width: itemWidth - 20,
                  opacity: textOpacity,
                  transform: `translateY(${
                    isAbove ? -textY : textY
                  }px)`,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 800,
                    color: "#22d3ee",
                    fontFamily: "sans-serif",
                    marginBottom: 8,
                  }}
                >
                  {event.year}
                </div>
                <div
                  style={{
                    fontSize: 17,
                    fontWeight: 500,
                    color: "#e2e8f0",
                    fontFamily: "sans-serif",
                    lineHeight: 1.4,
                  }}
                >
                  {event.label}
                </div>
              </div>
            </div>
          );
        })}
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