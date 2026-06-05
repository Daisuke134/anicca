#
# Kokoro TTS for Japanese phone calls — uses misaki[ja] g2p, NOT espeak.
#
# WHY THIS EXISTS (verified 2026-06-04): pipecat's stock KokoroTTSService routes
# Japanese through kokoro-onnx's default espeak phonemizer, which mangles
# Japanese into gibberish. Empirical proof:
#   "アニッチャです。次の予定まで二時間ないよ。今すぐ出ないと間に合わない。"
#     espeak path  -> 20.4s of garbage; Whisper read-back: "nitz desu en Chinese,
#                     yerれた yerれた …" (unintelligible)
#     misaki path  -> 5.5s natural; Whisper read-back: "兄っちゃんです。次の予定まで
#                     に時間ないよ。今すぐ出ないと間に合わない。" (correct)
# misaki[ja] is Kokoro's official Japanese g2p (pyopenjtalk-backed). We run it to
# IPA phonemes and feed them to kokoro-onnx with is_phonemes=True.
#

import re
from collections.abc import AsyncGenerator

import numpy as np
from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.settings import assert_given
from pipecat.utils.tracing.service_decorators import traced_tts

# Any hiragana, katakana, or CJK ideograph → treat the utterance as Japanese and
# phonemize via misaki. Pure-ASCII lines (the EN fallback when Dais speaks
# English) go through kokoro's native en-us path, which espeak handles fine.
_JA_CHAR = re.compile(r"[぀-ヿ㐀-鿿ｦ-ﾟ]")


class KokoroJaTTSService(KokoroTTSService):
    """Kokoro TTS whose Japanese is phonemized by misaki[ja] instead of espeak.

    Drop-in for KokoroTTSService — same Settings/voice/model handling; only
    run_tts is overridden to insert the misaki g2p step for Japanese text.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Imported lazily so the espeak-only stock service can still load if
        # misaki isn't installed; this subclass requires it.
        from misaki import ja as _misaki_ja

        self._ja_g2p = _misaki_ja.JAG2P()

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize speech, routing Japanese text through misaki g2p first."""
        logger.debug(f"{self}: Generating JA TTS [{text}]")
        try:
            await self.start_tts_usage_metrics(text)

            voice = assert_given(self._settings.voice)
            if voice is None:
                raise ValueError("Kokoro TTS voice must be specified")

            if _JA_CHAR.search(text):
                phonemes = self._ja_g2p(text)
                # misaki.ja.JAG2P returns a phoneme str (older builds returned a
                # (phonemes, tokens) tuple) — accept both.
                phonemes = phonemes[0] if isinstance(phonemes, tuple) else phonemes
                stream = self._kokoro.create_stream(
                    phonemes, voice=voice, lang="ja", is_phonemes=True, speed=1.0
                )
            else:
                stream = self._kokoro.create_stream(
                    text, voice=voice, lang="en-us", speed=1.0
                )

            async for samples, sample_rate in stream:
                await self.stop_ttfb_metrics()
                audio_int16 = (samples * 32767).astype(np.int16).tobytes()
                audio_data = await self._resampler.resample(
                    audio_int16, sample_rate, self.sample_rate
                )
                yield TTSAudioRawFrame(
                    audio=audio_data,
                    sample_rate=self.sample_rate,
                    num_channels=1,
                    context_id=context_id,
                )
        except Exception as e:
            logger.error(f"KokoroJaTTSService error: {e}")
            yield ErrorFrame(error=f"Kokoro JA TTS error: {e}")
        finally:
            await self.stop_ttfb_metrics()
