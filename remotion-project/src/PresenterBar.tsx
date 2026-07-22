import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import React from "react";

export const PresenterBar: React.FC<{
  topic: string;
  totalScenes: number;
  currentScene: number;
}> = ({ topic, totalScenes, currentScene }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Bar slides up from bottom on entry
  const barY = interpolate(frame, [0, 15], [60, 0], {
    extrapolateRight: "clamp",
  });

  // Progress bar fills based on current scene position
  const progressPercent = ((currentScene) / totalScenes) * 100;
  const progressWidth = interpolate(
    frame,
    [0, durationInFrames],
    [progressPercent, ((currentScene + 1) / totalScenes) * 100],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{ pointerEvents: "none" }}
    >
      {/* Bottom presenter bar */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          transform: `translateY(${barY}px)`,
        }}
      >
        {/* Progress bar line */}
        <div
          style={{
            width: "100%",
            height: 3,
            backgroundColor: "rgba(255,255,255,0.08)",
          }}
        >
          <div
            style={{
              width: `${progressWidth}%`,
              height: "100%",
              background: "linear-gradient(90deg, #6366f1, #06b6d4)",
              borderRadius: "0 2px 2px 0",
              transition: "width 0.1s linear",
            }}
          />
        </div>

        {/* Bar content */}
        <div
          style={{
            backgroundColor: "rgba(15, 23, 42, 0.92)",
            backdropFilter: "blur(10px)",
            padding: "10px 36px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: "1px solid rgba(99,102,241,0.2)",
          }}
        >
          {/* Left — Vidora branding */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366f1, #06b6d4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 800,
                color: "#fff",
                fontFamily: "sans-serif",
              }}
            >
              V
            </div>
            <span
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: "#ffffff",
                fontFamily: "sans-serif",
                letterSpacing: "0.5px",
              }}
            >
              Vidora
            </span>
          </div>

          {/* Center — Current topic */}
          <div
            style={{
              fontSize: 15,
              color: "#94a3b8",
              fontFamily: "sans-serif",
              fontWeight: 500,
              letterSpacing: "0.3px",
              textAlign: "center",
              maxWidth: 600,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {topic}
          </div>

          {/* Right — Scene counter */}
          <div
            style={{
              fontSize: 14,
              color: "#475569",
              fontFamily: "sans-serif",
              fontWeight: 500,
              letterSpacing: "0.5px",
            }}
          >
            {currentScene + 1} / {totalScenes}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};