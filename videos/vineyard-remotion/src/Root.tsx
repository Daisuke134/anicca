import React from "react";
import { Composition } from "remotion";
import { VineyardDemo, FPS, TOTAL_FRAMES } from "./VineyardDemo";
import { AgentLiveDemo, FPS_AGENT, TOTAL_FRAMES_AGENT } from "./AgentLiveDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VineyardDemo"
        component={VineyardDemo}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="AgentLiveDemo"
        component={AgentLiveDemo}
        durationInFrames={TOTAL_FRAMES_AGENT}
        fps={FPS_AGENT}
        width={1920}
        height={1080}
      />
    </>
  );
};
