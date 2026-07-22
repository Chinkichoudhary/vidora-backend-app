import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import React from "react";

export const DiagramScene: React.FC<{
  heading: string;
  steps: string[];
}> = ({ heading, steps }) => {
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

  // Timing: each box + its incoming arrow appears in sequence
  const START_DELAY = 30;
  const STAGGER = 35; // frames between each box appearing

  const boxWidth = 220;
  const boxGap = 60; // gap that the arrow occupies
  const totalWidth =
    steps.length * boxWidth + (steps.length - 1) * boxGap;
  const startX = (1280 - totalWidth) / 2;

  return (
    <AbsoluteFill
      style={{
        opacity: bgOpacity,
        background:
          "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        justifyContent: "flex-start",
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
          marginBottom: 70,
          letterSpacing: "-1px",
        }}
      >
        {heading}
      </div>

      {/* ── Flowchart row ── */}
      <div
        style={{
          position: "relative",
          width: 1280,
          height: 220,
        }}
      >
        {steps.map((step, index) => {
          const boxStartFrame = START_DELAY + index * STAGGER;
          const arrowStartFrame = boxStartFrame - 12;

          // Box pop-in
          const boxScale = interpolate(
            frame,
            [boxStartFrame, boxStartFrame + 12, boxStartFrame + 20],
            [0, 1.08, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );
          const boxOpacity = interpolate(
            frame,
            [boxStartFrame, boxStartFrame + 14],
            [0, 1],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          // Arrow grows in just before the NEXT box (skip arrow before first box)
          const arrowWidth = interpolate(
            frame,
            [arrowStartFrame, arrowStartFrame + 18],
            [0, boxGap],
            { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
          );

          const left = startX + index * (boxWidth + boxGap);

          return (
            <React.Fragment key={index}>
              {/* Arrow BEFORE this box (only if not the first box) */}
              {index > 0 && (
                <div
                  style={{
                    position: "absolute",
                    left: left - boxGap,
                    top: 100,
                    width: arrowWidth,
                    height: 4,
                    background:
                      "linear-gradient(90deg, #6366f1, #06b6d4)",
                    borderRadius: 2,
                  }}
                >
                  {/* Arrow head */}
                  <div
                    style={{
                      position: "absolute",
                      right: -2,
                      top: -6,
                      width: 0,
                      height: 0,
                      opacity: arrowWidth >= boxGap - 5 ? 1 : 0,
                      borderTop: "8px solid transparent",
                      borderBottom: "8px solid transparent",
                      borderLeft: "12px solid #06b6d4",
                    }}
                  />
                </div>
              )}

              {/* Step Box */}
              <div
                style={{
                  position: "absolute",
                  left,
                  top: 0,
                  width: boxWidth,
                  opacity: boxOpacity,
                  transform: `scale(${boxScale})`,
                  background: "rgba(99,102,241,0.15)",
                  border: "2px solid #6366f1",
                  borderRadius: 18,
                  padding: "26px 20px",
                  textAlign: "center",
                  boxShadow: "0 12px 30px rgba(99,102,241,0.25)",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    background:
                      "linear-gradient(135deg, #6366f1, #06b6d4)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 14px auto",
                  }}
                >
                  <span
                    style={{
                      color: "#fff",
                      fontWeight: 800,
                      fontSize: 16,
                      fontFamily: "sans-serif",
                    }}
                  >
                    {index + 1}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 600,
                    color: "#e2e8f0",
                    fontFamily: "sans-serif",
                    lineHeight: 1.4,
                  }}
                >
                  {step}
                </div>
              </div>
            </React.Fragment>
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