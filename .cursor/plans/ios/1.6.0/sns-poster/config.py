"""
SNS Poster Configuration
アカウントID、APIエンドポイント、投稿設定

戦略: 量で攻める。全アカウント「苦しみ軽減」コンテンツ。09:00 JST 一斉投稿。
Phase 1: TikTok 除外（ReelFarm 運用中、新アカウント作成待ち）
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
# Path: .cursor/plans/ios/sns-poster/config.py -> anicca-project
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# =============================================================================
# API Keys
# =============================================================================
# Postiz: replaced Blotato on 2026-05-07. Keep BLOTATO_API_KEY exported as a
# transitional alias so any straggler import doesn't crash; remove after grace
# period. New code should use POSTIZ_API_KEY exclusively.
POSTIZ_API_KEY = os.getenv("POSTIZ_API_KEY", "")
BLOTATO_API_KEY = POSTIZ_API_KEY  # DEPRECATED alias (Blotato → Postiz, 2026-05-07)
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")  # Phase 2 で使用

# =============================================================================
# API Endpoints
# =============================================================================
POSTIZ_BASE_URL = "https://api.postiz.com/public/v1"
BLOTATO_BASE_URL = POSTIZ_BASE_URL  # DEPRECATED alias
FAL_BASE_URL = "https://queue.fal.run"

# =============================================================================
# Postiz Integration Index (source of truth)
# =============================================================================
POSTIZ_INTEGRATIONS_PATH = Path(os.path.expanduser("~/.openclaw/state/postiz-integrations.json"))

# DRY_RUN switch — when true, postiz.py prints curl invocations instead of POSTing.
MIGRATION_DRY_RUN = os.getenv("MIGRATION_DRY_RUN", "").lower() in {"1", "true", "yes"}

# =============================================================================
# 接続アカウント (Blotato Account IDs)
#
# 戦略: 量で攻める。全アカウント「苦しみ軽減」コンテンツ。09:00 JST 統一。
# Phase 1: TikTok 除外（ReelFarm 運用中 → 新アカウント作成後に追加）
# =============================================================================

# Phase 1 対象（9アカウント）
ACCOUNTS = {
    # ---------------------------------------------------------------------
    # X (Twitter) - 苦しみ軽減コンテンツ（テキスト重視）
    # ---------------------------------------------------------------------
    # NOTE (2026-05-07): "id" fields are legacy Blotato accountIds — no longer used.
    # Postiz resolves by handle via ~/.openclaw/state/postiz-integrations.json.
    # If "postiz_handle" is None, no active Postiz integration exists for that account.
    "x_aniccaxxx": {
        "id": "11820",  # legacy
        "username": "@aniccaxxx",
        "platform": "twitter",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "@aniccaxxx",  # → cmm6d7m5703rwpr0yr5vtme3w
    },
    "x_aniccaen": {
        "id": "11852",  # legacy
        "username": "@aniccaen",
        "platform": "twitter",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # not yet onboarded to Postiz
    },

    # ---------------------------------------------------------------------
    # Instagram - 苦しみ軽減コンテンツ（ビジュアル重視）
    # ---------------------------------------------------------------------
    "ig_anicca_ai": {
        "id": "28896",
        "username": "@anicca.ai",
        "platform": "instagram",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # @anicca.ai not in Postiz index yet
    },
    "ig_anicca_japan": {
        "id": "28897",
        "username": "@anicca.japan",
        "platform": "instagram",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # @anicca.japan not in Postiz index yet
    },
    "ig_anicca_daily": {
        "id": "28682",
        "username": "@anicca.daily",
        "platform": "instagram",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # @anicca.daily not in Postiz index yet
    },
    # New Postiz-only IG handles (added during migration so they're addressable
    # by account_key from this script):
    "ig_anicchasan": {
        "id": None,
        "username": "@anicchasan",
        "platform": "instagram",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "@anicchasan",  # → cmmzujxpa04ujp30yxqpg1vci
    },
    "ig_anicca_monk": {
        "id": None,
        "username": "@anicca.monk",
        "platform": "instagram",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "@anicca.monk",  # → cmmzzg2es0539p30ycb94ayx0
    },

    # ---------------------------------------------------------------------
    # YouTube - 苦しみ軽減コンテンツ（動画）
    # ---------------------------------------------------------------------
    "youtube_en": {
        "id": "25421",
        "username": "Daisuke Narita (Anicca - AI Coaching app)",
        "platform": "youtube",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # legacy; reelclaw uses card-1 channels instead
    },
    "youtube_jp": {
        "id": "25646",
        "username": "@anicca.jp",
        "platform": "youtube",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,
    },
    # Postiz-only YouTube channels (reelclaw):
    "youtube_anicca_en_card_1": {
        "id": None,
        "username": "anicca-en-card-1",
        "platform": "youtube",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "anicca-en-card-1",  # → cmmzukbkw04ulp30yfvijrwio
    },
    "youtube_anicca_ja_card_1": {
        "id": None,
        "username": "anicca-ja-card-1",
        "platform": "youtube",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "anicca-ja-card-1",  # → cmn1oukj9012nnq0yqhouc3ib
    },

    # ---------------------------------------------------------------------
    # Threads - 苦しみ軽減コンテンツ（テキスト、カジュアル）
    # ---------------------------------------------------------------------
    "threads_japan": {
        "id": "4464",
        "username": "@anicca.japan",
        "platform": "threads",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # Threads not yet onboarded to Postiz
    },

    # ---------------------------------------------------------------------
    # Pinterest - 苦しみ軽減コンテンツ（美しい画像 + 啓発テキスト）
    # ---------------------------------------------------------------------
    "pinterest": {
        "id": "3965",
        "username": "@aniccaai",
        "platform": "pinterest",
        "board_id": "796996533995957618",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": None,  # Pinterest not yet onboarded to Postiz
    },

    # ---------------------------------------------------------------------
    # TikTok (Postiz-active, added during Blotato → Postiz migration 2026-05-07)
    # The old TIKTOK_EXCLUDED dict below is kept for historical reference.
    # ---------------------------------------------------------------------
    "tt_anicchasan": {
        "id": None,
        "username": "@anicchasan",
        "platform": "tiktok",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "@anicchasan",  # → cmlrv8jq000hun60yy57eaptx
    },
    "tt_anicca_monk": {
        "id": None,
        "username": "@anicca.monk",
        "platform": "tiktok",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "@anicca.monk",  # → cmlt171eq04d9r00yzzceb6bw
    },
    "tt_anicca_en_card_1": {
        "id": None,
        "username": "anicca-en-card-1",
        "platform": "tiktok",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "anicca-en-card-1",  # → cmn8y47do02mmo70yckb46dyu
    },
    "tt_anicca_ja_card_1": {
        "id": None,
        "username": "anicca-ja-card-1",
        "platform": "tiktok",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
        "postiz_handle": "anicca-ja-card-1",  # → cmnhlk3ju058lpn0ytilqdpo0
    },
}

# =============================================================================
# TikTok アカウント（Phase 1 除外 - ReelFarm 運用中）
# 新アカウント作成後に ACCOUNTS に追加する
# =============================================================================
TIKTOK_EXCLUDED = {
    "tt_anicca_ai": {
        "id": "27339",
        "username": "@anicca.ai",
        "platform": "tiktok",
        "lang": "EN",
        "status": "reelfarm_active",  # ReelFarm で運用中
    },
    "tt_anicca_japan": {
        "id": "27527",
        "username": "@anicca.japan",
        "platform": "tiktok",
        "lang": "JP",
        "status": "reelfarm_active",
    },
    "tt_anicca57": {
        "id": "27528",
        "username": "@anicca57",
        "platform": "tiktok",
        "lang": "EN",
        "status": "reelfarm_active",
    },
    "tt_anicca_self": {
        "id": "28152",
        "username": "@anicca.self",
        "platform": "tiktok",
        "lang": "EN",
        "status": "connected",  # 2026-01-27: Blotato接続完了
    },
    # 新アカウント作成後にここに追加 → ACCOUNTS に移動
    # "tt_new_jp": { "id": "???", "platform": "tiktok", "lang": "JP", "slots": ["09:00"] },
    # "tt_new_en": { "id": "???", "platform": "tiktok", "lang": "EN", "slots": ["09:00"] },
}

# =============================================================================
# コンテンツ4柱（Content Brain のローテーション）
# =============================================================================
CONTENT_PILLARS = {
    "demo": "アプリの機能を見せる（通知→NudgeCard→変化）",
    "story": "挫折→希望の物語（「6年間何も変われなかった」系）",
    "faceless": "テキスト動画（フック + 仏教的メッセージ + 字幕）",
    "mythbust": "「習慣アプリが全部失敗する本当の理由」系",
}

# =============================================================================
# アカウント検索ヘルパー
# =============================================================================
def get_accounts_by_lang(lang: str) -> list:
    """言語でアカウントを取得"""
    return [k for k, v in ACCOUNTS.items() if v.get("lang") == lang]

def get_accounts_by_platform(platform: str) -> list:
    """プラットフォームでアカウントを取得"""
    return [k for k, v in ACCOUNTS.items() if v.get("platform") == platform]

# =============================================================================
# Default Settings
# =============================================================================
DEFAULT_LINK = "https://anicca.app"
DEFAULT_HASHTAGS = {
    "EN": "#anicca #habits #selfimprovement #mindfulness #wellness #buddhism #mentalhealth",
    "JP": "#anicca #習慣化 #自己改善 #マインドフルネス #仏教 #行動変容 #メンタルヘルス",
}

# =============================================================================
# Generated Files Directory
# =============================================================================
GENERATED_DIR = PROJECT_ROOT / "generated"
IMAGES_DIR = GENERATED_DIR / "images"
VIDEOS_DIR = GENERATED_DIR / "videos"

# Ensure directories exist
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
