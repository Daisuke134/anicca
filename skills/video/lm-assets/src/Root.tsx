import { Composition } from "remotion";
import { MrBotCall } from "./MrBotCall";

// One 9:16 motion piece per script beat. Duration is passed in so it can be matched to the narration.
export const RemotionRoot: React.FC = () => (
  <Composition
    id="MrBotCall"
    component={MrBotCall}
    durationInFrames={30 * 15}
    fps={30}
    width={1080}
    height={1920}
  />
);
