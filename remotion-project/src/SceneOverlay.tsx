import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Character } from "./Characters";

const SIDE = 40;
const TOP = 30;
const BOTTOM = 72; // keeps clear of the presenter bar

const layout = (pos: string): React.CSSProperties => {
  const base: React.CSSProperties = {
    display: "flex",
    padding: `${TOP}px ${SIDE}px ${BOTTOM}px ${SIDE}px`,
    pointerEvents: "none",
  };
  switch (pos) {
    case "left":
      return { ...base, justifyContent: "flex-start", alignItems: "center" };
    case "top-right":
      return { ...base, justifyContent: "flex-end", alignItems: "flex-start" };
    case "bottom-right":
      return { ...base, justifyContent: "flex-end", alignItems: "flex-end" };
    case "bottom-left":
      return { ...base, justifyContent: "flex-start", alignItems: "flex-end" };
    default:
      return { ...base, justifyContent: "flex-end", alignItems: "center" };
  }
};

export const SceneOverlay: React.FC<{ scene: any }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const hasImage = !!scene.image_file;
  const hasChar = !!scene.character;
  if (!hasImage && !hasChar) return null;

  const pop = spring({
    frame: frame - 12,
    fps,
    config: { damping: 13, stiffness: 110, mass: 0.7 },
  });
  const fade = interpolate(frame, [12, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const imgW = ((scene.image_size || 26) / 100) * width;
  const charW = ((scene.char_size || 18) / 100) * width;

  return (
    <>
      {hasImage && (
        <AbsoluteFill style={layout(scene.image_pos || "top-right")}>
          <div
            style={{
              width: imgW,
              opacity: fade,
              transform: `scale(${0.85 + 0.15 * pop})`,
              borderRadius: 20,
              overflow: "hidden",
              border: "3px solid rgba(255,255,255,0.18)",
              boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
            }}
          >
            <Img
              src={staticFile(`media/${scene.image_file}`)}
              style={{
                width: "100%",
                aspectRatio: "4 / 3",
                objectFit: "cover",
                display: "block",
              }}
            />
          </div>
        </AbsoluteFill>
      )}
      {hasChar && (
        <AbsoluteFill style={layout(scene.char_pos || "bottom-right")}>
          <div
            style={{
              width: charW,
              height: charW * 1.2,
              opacity: fade,
              transform: `translateY(${(1 - pop) * 60}px) scale(${0.8 + 0.2 * pop})`,
              transformOrigin: "bottom center",
            }}
          >
            <Character name={scene.character} />
          </div>
        </AbsoluteFill>
      )}
    </>
  );
};