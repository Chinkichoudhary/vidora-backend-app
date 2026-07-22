import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
} from "remotion";
import React from "react";

export const SceneTransition: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, 8, 12],
    [1, 0.6, 0],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0f172a",
        opacity,
        pointerEvents: "none",
        zIndex: 100,
      }}
    />
  );
};