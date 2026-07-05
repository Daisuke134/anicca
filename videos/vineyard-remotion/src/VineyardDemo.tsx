import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

export const FPS = 30;
export const SCENE_TITLE = 90; // 3.0s
export const SCENE_WALLET = 105; // 3.5s
export const SCENE_ENGINES = 90; // 3.0s
export const SCENE_COUNTER = 150; // 5.0s
export const SCENE_CLOSE = 54; // 1.8s
export const TOTAL_FRAMES =
  SCENE_TITLE + SCENE_WALLET + SCENE_ENGINES + SCENE_COUNTER + SCENE_CLOSE;

const GREEN = "#7fe3a3";
const BG = "#05070a";

function FadeUp({
  children,
  delay = 0,
  duration = 15,
  distance = 26,
}: {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  distance?: number;
}) {
  const frame = useCurrentFrame();
  const t = frame - delay;
  const opacity = interpolate(t, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(t, [0, duration], [distance, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return <div style={{ opacity, transform: `translateY(${y}px)` }}>{children}</div>;
}

function SceneTitle() {
  return (
    <AbsoluteFill
      style={{
        background: BG,
        color: "#f5f7fa",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
        textAlign: "center",
      }}
    >
      <FadeUp delay={3} duration={15}>
        <div
          style={{
            fontSize: 34,
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: GREEN,
            marginBottom: 28,
          }}
        >
          Vineyard
        </div>
      </FadeUp>
      <FadeUp delay={8} duration={18}>
        <div style={{ fontSize: 112, fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1.05 }}>
          An AI with
          <br />
          its own wallet.
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

function SceneWallet() {
  return (
    <AbsoluteFill
      style={{
        background: BG,
        color: "#f5f7fa",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
        textAlign: "center",
      }}
    >
      <FadeUp delay={2} duration={12}>
        <div
          style={{
            fontSize: 34,
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: GREEN,
            marginBottom: 28,
          }}
        >
          Spawn
        </div>
      </FadeUp>
      <FadeUp delay={7} duration={15}>
        <div style={{ fontSize: 84, fontWeight: 800, letterSpacing: "-0.02em" }}>
          Instance #a3f9 is born.
        </div>
      </FadeUp>
      <FadeUp delay={18} duration={15} distance={0}>
        <div
          style={{
            marginTop: 40,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 40,
            color: GREEN,
            background: "rgba(127, 227, 163, 0.1)",
            border: "2px solid rgba(127, 227, 163, 0.35)",
            borderRadius: 999,
            padding: "18px 44px",
          }}
        >
          0x7c2e...9a41
        </div>
      </FadeUp>
      <FadeUp delay={33} duration={15}>
        <div style={{ marginTop: 30, fontSize: 44, fontWeight: 500, color: "#b7bfca", maxWidth: 1400 }}>
          No human clicked a button. No human holds the key.
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

function SceneEngines() {
  const frame = useCurrentFrame();
  const engines = ["Polymarket", "Yield", "Hyperliquid", "Solana"];
  const pickedScale = spring({
    frame: frame - 24,
    fps: FPS,
    config: { damping: 10, stiffness: 140 },
  });
  return (
    <AbsoluteFill
      style={{
        background: BG,
        color: "#f5f7fa",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
        textAlign: "center",
      }}
    >
      <FadeUp delay={2} duration={12}>
        <div
          style={{
            fontSize: 34,
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: GREEN,
            marginBottom: 28,
          }}
        >
          Earn Loop
        </div>
      </FadeUp>
      <FadeUp delay={7} duration={15}>
        <div style={{ fontSize: 72, fontWeight: 800 }}>It picks. It trades. It earns.</div>
      </FadeUp>
      <div style={{ display: "flex", gap: 48, marginTop: 56 }}>
        {engines.map((name, i) => {
          const picked = name === "Yield";
          const cardOpacity = interpolate(frame - (14 + i * 2), [0, 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={name}
              style={{
                opacity: cardOpacity,
                width: 300,
                padding: "40px 24px",
                borderRadius: 28,
                background: picked ? "rgba(127, 227, 163, 0.14)" : "rgba(255,255,255,0.04)",
                border: `2px solid ${picked ? GREEN : "rgba(255,255,255,0.12)"}`,
                color: picked ? GREEN : "#f5f7fa",
                fontSize: 38,
                fontWeight: 700,
                transform: picked ? `scale(${1 + pickedScale * 0.06})` : undefined,
              }}
            >
              {name}
            </div>
          );
        })}
      </div>
      <FadeUp delay={49} duration={12}>
        <div
          style={{
            marginTop: 50,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 32,
            color: GREEN,
          }}
        >
          tx confirmed: 0x91fa...&nbsp;&nbsp;status 0x1
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

function SceneCounter() {
  const frame = useCurrentFrame();
  const target = 47.82;
  const countDuration = 95; // frames (~3.16s @30fps)
  const rawValue = interpolate(frame, [0, countDuration], [0, target], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.linear,
  });
  const landed = frame >= countDuration;
  const flashOpacity = interpolate(
    frame,
    [countDuration, countDuration + 3, countDuration + 26, countDuration + 30],
    [0, 0.34, 0.18, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const popScale = landed
    ? spring({ frame: frame - countDuration, fps: FPS, config: { damping: 9, stiffness: 200 } })
    : 0;
  const labelOpacity = interpolate(frame, [12, 27], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "#fdfefe",
        color: "#111315",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
      }}
    >
      <div style={{ position: "absolute", inset: 0, background: "#30d158", opacity: flashOpacity }} />
      <div
        style={{
          position: "relative",
          fontSize: 190,
          fontWeight: 900,
          fontVariantNumeric: "tabular-nums",
          color: landed ? "#30d158" : "#111315",
          transform: `scale(${1 + (landed ? popScale * 0.06 : 0)})`,
        }}
      >
        ${rawValue.toFixed(2)}
      </div>
      <div
        style={{
          marginTop: 28,
          fontSize: 40,
          fontWeight: 700,
          color: "#4a4f57",
          opacity: labelOpacity,
          textAlign: "center",
        }}
      >
        Vineyard instance #a3f9 — real ledger, ticking live
      </div>
    </AbsoluteFill>
  );
}

function SceneClose() {
  const frame = useCurrentFrame();
  const scale = spring({ frame, fps: FPS, config: { damping: 11, stiffness: 130 } });
  return (
    <AbsoluteFill
      style={{
        background: BG,
        color: "#f5f7fa",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 96, fontWeight: 900, letterSpacing: "-0.02em", transform: `scale(${scale})` }}>
        VINEYARD
      </div>
      <FadeUp delay={10} duration={15}>
        <div style={{ marginTop: 20, fontSize: 40, fontWeight: 500, color: "#b7bfca" }}>
          Financially independent. Zero humans in the loop.
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

export const VineyardDemo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={SCENE_TITLE}>
        <SceneTitle />
      </Sequence>
      <Sequence from={SCENE_TITLE} durationInFrames={SCENE_WALLET}>
        <SceneWallet />
      </Sequence>
      <Sequence from={SCENE_TITLE + SCENE_WALLET} durationInFrames={SCENE_ENGINES}>
        <SceneEngines />
      </Sequence>
      <Sequence
        from={SCENE_TITLE + SCENE_WALLET + SCENE_ENGINES}
        durationInFrames={SCENE_COUNTER}
      >
        <SceneCounter />
      </Sequence>
      <Sequence
        from={SCENE_TITLE + SCENE_WALLET + SCENE_ENGINES + SCENE_COUNTER}
        durationInFrames={SCENE_CLOSE}
      >
        <SceneClose />
      </Sequence>
    </AbsoluteFill>
  );
};
