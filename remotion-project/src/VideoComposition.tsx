import { Series, AbsoluteFill, Audio, staticFile } from "remotion";
import React from "react";
import { TitleIntro } from "./TitleIntro";
import { DefinitionScene } from "./DefinitionScene";
import { BulletScene } from "./BulletScene";
import { ComparisonScene } from "./ComparisonScene";
import { DiagramScene } from "./DiagramScene";
import { TimelineScene } from "./TimelineScene";
import { StatsScene } from "./StatsScene";
import { IconGridScene } from "./IconGridScene";
import { QuoteScene } from "./QuoteScene";
import { OutroScene } from "./OutroScene";
import { PresenterBar } from "./PresenterBar";
import { SceneTransition } from "./SceneTransition";

const SCENE_DURATIONS: Record<string, number> = {
  TitleIntro: 150,
  DefinitionScene: 180,
  BulletScene: 210,
  ComparisonScene: 270,
  DiagramScene: 270,
  TimelineScene: 270,
  StatsScene: 210,
  IconGridScene: 240,
  QuoteScene: 180,
  OutroScene: 210,
};

const renderScene = (scene: any): React.ReactNode => {
  switch (scene.type) {
    case "TitleIntro":
      return <TitleIntro topic={scene.topic} />;
    case "DefinitionScene":
      return (
        <DefinitionScene
          term={scene.term}
          explanation={scene.explanation}
        />
      );
    case "BulletScene":
      return (
        <BulletScene
          heading={scene.heading}
          points={scene.points}
        />
      );
    case "ComparisonScene":
      return (
        <ComparisonScene
          heading={scene.heading}
          leftTitle={scene.leftTitle}
          leftPoints={scene.leftPoints}
          rightTitle={scene.rightTitle}
          rightPoints={scene.rightPoints}
        />
      );
    case "DiagramScene":
      return (
        <DiagramScene
          heading={scene.heading}
          steps={scene.steps}
        />
      );
    case "TimelineScene":
      return (
        <TimelineScene
          heading={scene.heading}
          events={scene.events}
        />
      );
    case "StatsScene":
      return (
        <StatsScene
          label={scene.label}
          number={scene.number}
          suffix={scene.suffix}
          description={scene.description}
        />
      );
    case "IconGridScene":
      return (
        <IconGridScene
          heading={scene.heading}
          description={scene.description}
          iconNames={scene.iconNames}
        />
      );
    case "QuoteScene":
      return (
        <QuoteScene
          quote={scene.quote}
          attribution={scene.attribution}
        />
      );
    case "OutroScene":
      return (
        <OutroScene
          summary={scene.summary}
          ctaText={scene.ctaText}
        />
      );
    default:
      return null;
  }
};

const getTopic = (scenes: any[]): string => {
  const titleScene = scenes.find((s) => s.type === "TitleIntro");
  return titleScene ? titleScene.topic : "Educational Video";
};

export const VideoComposition: React.FC<{ scenes: any[] }> = ({
  scenes,
}) => {
  const topic = getTopic(scenes);
  const totalScenes = scenes.length;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      <Series>
        {scenes.map((scene, index) => {
          const duration = SCENE_DURATIONS[scene.type] || 150;
          const rendered = renderScene(scene);
          if (!rendered) return null;

          return (
            <Series.Sequence
              key={index}
              durationInFrames={scene.duration_frames || duration}
            >
              {/* Scene content */}
              <AbsoluteFill>
                {rendered}
              </AbsoluteFill>

              {/* Audio for this scene */}
              {scene.audio_file && (
  <Audio src={staticFile(`audio/${scene.audio_file}`)} />
)}

              {/* Presenter bar overlaid on every scene */}
              <PresenterBar
                topic={topic}
                totalScenes={totalScenes}
                currentScene={index}
              />

              {/* Transition flash at start of each scene */}
              <SceneTransition />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};