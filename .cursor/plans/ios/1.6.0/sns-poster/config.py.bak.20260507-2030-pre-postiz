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
BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY", "")
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")  # Phase 2 で使用

# =============================================================================
# API Endpoints
# =============================================================================
BLOTATO_BASE_URL = "https://backend.blotato.com/v2"
FAL_BASE_URL = "https://queue.fal.run"

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
    "x_aniccaxxx": {
        "id": "11820",
        "username": "@aniccaxxx",
        "platform": "twitter",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
    },
    "x_aniccaen": {
        "id": "11852",
        "username": "@aniccaen",
        "platform": "twitter",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
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
    },
    "ig_anicca_japan": {
        "id": "28897",
        "username": "@anicca.japan",
        "platform": "instagram",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
    },
    "ig_anicca_daily": {
        "id": "28682",
        "username": "@anicca.daily",
        "platform": "instagram",
        "lang": "EN",
        "frequency": 1,
        "slots": ["09:00"],
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
    },
    "youtube_jp": {
        "id": "25646",
        "username": "@anicca.jp",  # Reviewer Test (Anicca)
        "platform": "youtube",
        "lang": "JP",
        "frequency": 1,
        "slots": ["09:00"],
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
