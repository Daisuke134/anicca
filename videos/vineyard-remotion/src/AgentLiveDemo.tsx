import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  interpolate,
  spring,
  Easing,
} from "remotion";

export const FPS_AGENT = 30;
export const SCENE_HEADER = 60; // 2.0s
export const SCENE_NETWORTH = 90; // 3.0s
export const SCENE_REVENUE_CELLS = 60; // 2.0s
export const SCENE_REVENUE_SOURCES = 60; // 2.0s
export const SCENE_LIVE_LOG = 60; // 2.0s
export const SCENE_AGENT_CLOSE = 30; // 1.0s
export const TOTAL_FRAMES_AGENT =
  SCENE_HEADER +
  SCENE_NETWORTH +
  SCENE_REVENUE_CELLS +
  SCENE_REVENUE_SOURCES +
  SCENE_LIVE_LOG +
  SCENE_AGENT_CLOSE;

// ---- design tokens, matching aniccaai.com/agent AgentClient.tsx visual language ----
const BG_LIGHT = "#fdfefe";
const TEXT_DARK = "#111315";
const MUTED = "#6b7280";
const GOLD = "#b8923f";
const GREEN = "#3a9d6e";
const RED = "#c0392b";
const STATUS_GREEN = "#3a9d6e";
const BORDER = "rgba(0,0,0,0.1)";
const BG_DARK = "#05070a";
const MONO = "'JetBrains Mono', monospace";
const SANS = "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif";

const HOST = "anicca-a3cdd4";
const URL_TEXT = `aniccaai.com/agent?id=${HOST}`;

const NET_WORTH_USD = 1.2053946313910322;
const DAILY_REVENUE = "−$0.0997";
const MONTHLY_REVENUE = "−$0.1099";

const REVENUE_SOURCES: { name: string; value: string }[] = [
  { name: "hl", value: "+$0.0492" },
  { name: "hl-trade", value: "+$0.2311" },
  { name: "morpho", value: "+$0.0015" },
  { name: "moonwell", value: "+$0.0019" },
];

const LOG_LINES = [
  "wake · earn/clip-producer",
  "wake · hl_trade",
  "wake · yield",
  "wake · earn/polymarket-trade",
  "skill_error · earn/sol-trade",
  "wake · x402_sell",
];

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

function SceneAgentHeader() {
  const frame = useCurrentFrame();
  const dotFade = interpolate(frame - 10, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const dotPop = spring({
    frame: frame - 10,
    fps: FPS_AGENT,
    config: { damping: 8, stiffness: 120 },
  });
  const dotScale = 1 + dotPop * 0.3;

  return (
    <AbsoluteFill
      style={{
        background: BG_LIGHT,
        color: TEXT_DARK,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: SANS,
        textAlign: "center",
      }}
    >
      <FadeUp delay={3} duration={15} distance={14}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 30,
            color: MUTED,
            marginBottom: 26,
            letterSpacing: "0.01em",
          }}
        >
          {URL_TEXT}
        </div>
      </FadeUp>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <div
          style={{
            width: 16,
            height: 16,
            borderRadius: 8,
            background: STATUS_GREEN,
            boxShadow: "0 0 10px rgba(58,157,110,0.6)",
            opacity: dotFade,
            transform: `scale(${dotScale})`,
          }}
        />
        <FadeUp delay={18} duration={16} distance={20}>
          <div style={{ fontSize: 96, fontWeight: 800, letterSpacing: "-0.02em" }}>
            {HOST}
          </div>
        </FadeUp>
      </div>
      <FadeUp delay={34} duration={16} distance={10}>
        <div style={{ marginTop: 26, fontSize: 30, fontWeight: 500, color: MUTED }}>
          frozen live snapshot · 2026-07-05
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

function SceneNetWorth() {
  const frame = useCurrentFrame();
  const countDuration = 70;
  const rawValue = interpolate(frame, [0, countDuration], [0, NET_WORTH_USD], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.linear,
  });
  const landed = frame >= countDuration;
  const flashOpacity = interpolate(
    frame,
    [countDuration, countDuration + 3, countDuration + 26, countDuration + 30],
    [0, 0.3, 0.15, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const popScale = landed
    ? spring({ frame: frame - countDuration, fps: FPS_AGENT, config: { damping: 9, stiffness: 200 } })
    : 0;
  const labelOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: BG_LIGHT,
        color: TEXT_DARK,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: SANS,
      }}
    >
      <div style={{ position: "absolute", inset: 0, background: GOLD, opacity: flashOpacity }} />
      <div
        style={{
          fontSize: 32,
          fontWeight: 600,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: MUTED,
          opacity: labelOpacity,
          marginBottom: 20,
        }}
      >
        Net Worth
      </div>
      <div
        style={{
          position: "relative",
          fontSize: 176,
          fontWeight: 900,
          fontVariantNumeric: "tabular-nums",
          fontFamily: MONO,
          color: landed ? GOLD : TEXT_DARK,
          transform: `scale(${1 + (landed ? popScale * 0.06 : 0)})`,
        }}
      >
        ${rawValue.toFixed(2)}
      </div>
      <div
        style={{
          marginTop: 26,
          fontSize: 34,
          fontWeight: 500,
          color: MUTED,
          opacity: labelOpacity,
          textAlign: "center",
        }}
      >
        {HOST} — real ledger, zero humans in the loop
      </div>
    </AbsoluteFill>
  );
}

function RevenueCell({
  label,
  value,
  delay,
}: {
  label: string;
  value: string;
  delay: number;
}) {
  return (
    <FadeUp delay={delay} duration={16} distance={30}>
      <div
        style={{
          width: 480,
          padding: "44px 40px",
          borderRadius: 20,
          border: `1px solid ${BORDER}`,
          background: "#ffffff",
          textAlign: "left",
        }}
      >
        <div
          style={{
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: MUTED,
            marginBottom: 16,
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 64,
            fontWeight: 800,
            fontVariantNumeric: "tabular-nums",
            color: RED,
          }}
        >
          {value}
        </div>
      </div>
    </FadeUp>
  );
}

function SceneRevenueCells() {
  return (
    <AbsoluteFill
      style={{
        background: BG_LIGHT,
        color: TEXT_DARK,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "row",
        gap: 40,
        fontFamily: SANS,
      }}
    >
      <RevenueCell label="Revenue today" value={DAILY_REVENUE} delay={0} />
      <RevenueCell label="Revenue this month" value={MONTHLY_REVENUE} delay={10} />
    </AbsoluteFill>
  );
}

function SceneRevenueSources() {
  const frame = useCurrentFrame();
  const labelOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        background: BG_LIGHT,
        color: TEXT_DARK,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: SANS,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: MUTED,
          opacity: labelOpacity,
          marginBottom: 44,
        }}
      >
        Revenue by Source
      </div>
      <div style={{ display: "flex", gap: 32 }}>
        {REVENUE_SOURCES.map((source, i) => {
          const cardOpacity = interpolate(frame - (12 + i * 8), [0, 14], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const cardY = interpolate(frame - (12 + i * 8), [0, 14], [22, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          });
          return (
            <div
              key={source.name}
              style={{
                opacity: cardOpacity,
                transform: `translateY(${cardY}px)`,
                width: 300,
                padding: "36px 28px",
                borderRadius: 20,
                border: `1px solid ${BORDER}`,
                background: "#ffffff",
                textAlign: "left",
              }}
            >
              <div style={{ fontFamily: MONO, fontSize: 26, color: MUTED, marginBottom: 14 }}>
                {source.name}
              </div>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: 44,
                  fontWeight: 800,
                  color: GREEN,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {source.value}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

function SceneLiveLog() {
  const frame = useCurrentFrame();
  const labelOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        background: BG_LIGHT,
        color: TEXT_DARK,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: SANS,
      }}
    >
      <div
        style={{
          fontSize: 26,
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: MUTED,
          opacity: labelOpacity,
          marginBottom: 30,
        }}
      >
        Live Activity — streamed from the agent&apos;s own ledger
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 720 }}>
        {LOG_LINES.map((line, i) => (
          <FadeUp key={line} delay={6 + i * 8} duration={10} distance={16}>
            <div
              style={{
                fontFamily: MONO,
                fontSize: 32,
                color: line.startsWith("skill_error") ? RED : TEXT_DARK,
                padding: "10px 20px",
                borderRadius: 10,
                background: "rgba(0,0,0,0.03)",
              }}
            >
              {line}
            </div>
          </FadeUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

function SceneAgentClose() {
  const frame = useCurrentFrame();
  const scale = spring({ frame, fps: FPS_AGENT, config: { damping: 11, stiffness: 130 } });
  return (
    <AbsoluteFill
      style={{
        background: BG_DARK,
        color: "#f5f7fa",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        fontFamily: SANS,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 88,
          fontWeight: 900,
          letterSpacing: "-0.02em",
          transform: `scale(${scale})`,
        }}
      >
        Zero humans in the loop.
      </div>
      <FadeUp delay={8} duration={14} distance={12}>
        <div
          style={{
            marginTop: 24,
            fontFamily: MONO,
            fontSize: 30,
            color: "#b7bfca",
          }}
        >
          {URL_TEXT}
        </div>
      </FadeUp>
    </AbsoluteFill>
  );
}

export const AgentLiveDemo: React.FC = () => {
  const f1 = SCENE_HEADER;
  const f2 = f1 + SCENE_NETWORTH;
  const f3 = f2 + SCENE_REVENUE_CELLS;
  const f4 = f3 + SCENE_REVENUE_SOURCES;
  const f5 = f4 + SCENE_LIVE_LOG;

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={SCENE_HEADER}>
        <SceneAgentHeader />
      </Sequence>
      <Sequence from={f1} durationInFrames={SCENE_NETWORTH}>
        <SceneNetWorth />
      </Sequence>
      <Sequence from={f2} durationInFrames={SCENE_REVENUE_CELLS}>
        <SceneRevenueCells />
      </Sequence>
      <Sequence from={f3} durationInFrames={SCENE_REVENUE_SOURCES}>
        <SceneRevenueSources />
      </Sequence>
      <Sequence from={f4} durationInFrames={SCENE_LIVE_LOG}>
        <SceneLiveLog />
      </Sequence>
      <Sequence from={f5} durationInFrames={SCENE_AGENT_CLOSE}>
        <SceneAgentClose />
      </Sequence>
    </AbsoluteFill>
  );
};
