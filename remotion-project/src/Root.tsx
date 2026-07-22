import React from "react";
import { Composition } from "remotion";
import { TitleScene } from "./HelloWorld";
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
import { VideoComposition } from "./VideoComposition";
import { sampleScenes } from "./sampleScenes";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TitleScene"
        component={TitleScene}
        durationInFrames={300}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          title: "How Does the Brain Work?",
          subtitle: "Understanding the most complex organ in the human body",
        }}
      />
      <Composition
        id="TitleIntro"
        component={TitleIntro}
        durationInFrames={90}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          topic: "How Does the Brain Work?",
        }}
      />
      <Composition
        id="DefinitionScene"
        component={DefinitionScene}
        durationInFrames={120}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          term: "Neuron",
          explanation: "A specialized cell in the nervous system that receives, processes, and transmits information through electrical and chemical signals.",
        }}
      />
      <Composition
        id="BulletScene"
        component={BulletScene}
        durationInFrames={150}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          heading: "3 Main Parts of the Brain",
          points: [
            "Cerebrum – controls thinking, memory, and voluntary movement",
            "Cerebellum – manages balance and coordination",
            "Brainstem – controls breathing, heart rate, and reflexes",
          ],
        }}
      />
      <Composition
        id="ComparisonScene"
        component={ComparisonScene}
        durationInFrames={210}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          heading: "Mitosis vs Meiosis",
          leftTitle: "Mitosis",
          leftPoints: [
            "Produces 2 identical daughter cells",
            "Used for growth and repair",
            "One division cycle",
          ],
          rightTitle: "Meiosis",
          rightPoints: [
            "Produces 4 genetically different cells",
            "Used for sexual reproduction",
            "Two division cycles",
          ],
        }}
      />
      <Composition
        id="DiagramScene"
        component={DiagramScene}
        durationInFrames={210}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          heading: "Steps of Photosynthesis",
          steps: [
            "Sunlight absorbed by leaves",
            "Water drawn from roots",
            "CO2 taken from air",
            "Glucose & oxygen produced",
          ],
        }}
      />
      <Composition
        id="TimelineScene"
        component={TimelineScene}
        durationInFrames={210}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          heading: "Evolution of Computers",
          events: [
            { year: "1940s", label: "First electronic computers" },
            { year: "1970s", label: "Personal computers introduced" },
            { year: "1990s", label: "Internet becomes mainstream" },
            { year: "2020s", label: "AI-powered computing" },
          ],
        }}
      />
      <Composition
        id="StatsScene"
        component={StatsScene}
        durationInFrames={150}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          label: "Did You Know?",
          number: 86,
          suffix: "Billion",
          description: "Your brain contains approximately 86 billion neurons, each connected to thousands of others.",
        }}
      />
      <Composition
        id="IconGridScene"
        component={IconGridScene}
        durationInFrames={180}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          heading: "What is a Derivative?",
          description: "A derivative is a financial security with a value that is reliant upon an underlying asset or group of assets.",
          iconNames: ["Wallet", "Award", "Coins", "TrendingUp", "Droplet", "Percent"],
        }}
      />
      <Composition
        id="QuoteScene"
        component={QuoteScene}
        durationInFrames={120}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          quote: "The brain uses about 20% of the body's total energy, despite being only 2% of its weight.",
          attribution: "Key Takeaway",
        }}
      />
      <Composition
        id="OutroScene"
        component={OutroScene}
        durationInFrames={150}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          summary: "The brain is the control center of the body, made up of billions of neurons working together.",
          ctaText: "Watch Next Video",
        }}
      />
      <Composition
        id="FullVideo"
        component={VideoComposition}
        durationInFrames={sampleScenes.reduce((total, scene) => {
          const durations: Record<string, number> = {
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
          const sceneDuration =
            (scene as any).duration_frames ||
            durations[(scene as any).type] ||
            150;
          return total + sceneDuration;
        }, 0)}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          scenes: sampleScenes,
        }}
      />
    </>
  );
};