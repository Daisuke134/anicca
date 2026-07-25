import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// Purpose-built Life Manager b-roll. It shows the product's own moments — a clock you keep checking,
// the call that arrives before you have to leave, travel time filling itself in — as motion rather than
// as footage. No narration text is drawn here: MPT owns the subtitle layer, so nothing can double up.

const INK = "#0B0D10";
const FG = "#F2F4F7";
const MUTED = "#8A94A6";
const ACCENT = "#4ADE80";
const CALL = "#22C55E";

const Phone: React.FC<{ children: React.ReactNode; lift: number }> = ({ children, lift }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div
      style={{
        width: 760,
        height: 1500,
        borderRadius: 84,
        background: "linear-gradient(160deg,#14181E 0%,#0B0D10 60%)",
        border: `2px solid #232A34`,
        boxShadow: `0 60px 140px rgba(0,0,0,.65)`,
        transform: `translateY(${lift}px)`,
        overflow: "hidden",
        position: "relative",
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

const ClockFace: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  const seconds = frame / fps;
  // The minute hand crawls while the snooze pulse repeats — the feeling of time leaking away.
  const minute = interpolate(seconds, [0, 5], [0, 300]);
  const pulse = 1 + 0.06 * Math.sin(seconds * 6);
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          width: 420,
          height: 420,
          borderRadius: "50%",
          border: `10px solid ${MUTED}`,
          transform: `scale(${pulse})`,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 8,
            height: 150,
            background: FG,
            borderRadius: 8,
            transformOrigin: "50% 100%",
            transform: `translate(-50%,-100%) rotate(${minute}deg)`,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: 8,
            height: 100,
            background: MUTED,
            borderRadius: 8,
            transformOrigin: "50% 100%",
            transform: `translate(-50%,-100%) rotate(${minute / 12}deg)`,
          }}
        />
      </div>
    </div>
  );
};

const IncomingCall: React.FC<{ progress: number; frame: number; fps: number }> = ({ progress, frame, fps }) => {
  const ring = 1 + 0.05 * Math.sin((frame / fps) * 12);
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        right: 48,
        top: 220,
        transform: `translateY(${interpolate(progress, [0, 1], [220, 0])}px)`,
        opacity: progress,
      }}
    >
      <div
        style={{
          background: "#161B22",
          border: "1px solid #232A34",
          borderRadius: 40,
          padding: "56px 48px",
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <div style={{ color: MUTED, fontSize: 34, letterSpacing: 2 }}>INCOMING CALL</div>
        <div style={{ color: FG, fontSize: 74, fontWeight: 700 }}>Life Manager</div>
        <div style={{ color: ACCENT, fontSize: 40 }}>leave in 10 min</div>
        <div style={{ display: "flex", gap: 28, marginTop: 26 }}>
          <div
            style={{
              width: 132,
              height: 132,
              borderRadius: "50%",
              background: CALL,
              transform: `scale(${ring})`,
            }}
          />
          <div style={{ width: 132, height: 132, borderRadius: "50%", background: "#2A313B" }} />
        </div>
      </div>
    </div>
  );
};

const TravelFill: React.FC<{ progress: number }> = ({ progress }) => (
  <div style={{ position: "absolute", left: 48, right: 48, top: 260, opacity: progress }}>
    {["09:30  Design review", "", "18:00  Dinner"].map((label, index) =>
      label === "" ? (
        <div key={index} style={{ margin: "22px 0" }}>
          <div style={{ color: MUTED, fontSize: 30, marginBottom: 12 }}>TRAVEL</div>
          <div style={{ height: 96, borderRadius: 24, background: "#161B22", overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${interpolate(progress, [0, 1], [0, 100])}%`,
                background: `linear-gradient(90deg,#1F6F43,${ACCENT})`,
              }}
            />
          </div>
        </div>
      ) : (
        <div
          key={index}
          style={{
            background: "#12161C",
            border: "1px solid #232A34",
            borderRadius: 24,
            padding: "34px 30px",
            color: FG,
            fontSize: 40,
            margin: "22px 0",
          }}
        >
          {label}
        </div>
      ),
    )}
  </div>
);

export const LifeManagerCall: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const beat = durationInFrames / 3;

  const lift = spring({ frame, fps, config: { damping: 200 } }) * -10;
  const callIn = spring({ frame: frame - beat, fps, config: { damping: 200 } });
  const travelIn = spring({ frame: frame - beat * 2, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ background: INK, fontFamily: "Helvetica, Arial, sans-serif" }}>
      <Phone lift={lift}>
        {frame < beat * 2 ? <ClockFace frame={frame} fps={fps} /> : null}
        {frame >= beat && frame < beat * 2 ? <IncomingCall progress={callIn} frame={frame} fps={fps} /> : null}
        {frame >= beat * 2 ? <TravelFill progress={travelIn} /> : null}
      </Phone>
    </AbsoluteFill>
  );
};
