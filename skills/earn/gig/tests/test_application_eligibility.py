from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "application_eligibility.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "application_eligibility",
        MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load application_eligibility")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rejects_the_live_synchronous_interview_incident() -> None:
    module = load_module()
    brief = """
    現職でITエンジニアとして勤務している方を対象に、
    オンラインヒアリングにご協力いただける方を募集しています。
    所要時間は60分〜90分程度です。条件に合う方へ日程調整をご案内します。
    """
    proposal = """
    転職活動全体を非同期に整理しながら前に進める支援をご提案します。
    求人を整理し、応募判断の基準と書類の改善案をお渡しします。
    """

    verdict = module.evaluate_application(brief, proposal)

    assert verdict["allowed"] is False
    assert "synchronous_live_presence_required" in verdict["reason_codes"]
    assert "buyer_participant_seller_provider_role_mismatch" in verdict["reason_codes"]


def test_rejects_a_scheduled_client_interview_hidden_in_the_form() -> None:
    module = load_module()
    brief = "生成AIを活用した業務自動化を、完全在宅でお願いします。"
    proposal = "業務フローを棚卸しし、自動化ツールと手順書を納品します。"
    form_text = """
    エントリーが通過した際にクライアント面談を行うため、
    8月6日の13:00のご対応は可能でしょうか。
    """

    verdict = module.evaluate_application(brief, proposal, form_text=form_text)

    assert verdict["allowed"] is False
    assert verdict["reason_codes"] == ["synchronous_live_presence_required"]


def test_allows_recurring_asynchronous_chat_and_connected_account_work() -> None:
    module = load_module()
    brief = """
    コミュニケーションはココナラのチャット形式で、隙間時間で対応可能です。
    LINEとInstagramの投稿カレンダー、月次レポート、定期投稿をお願いします。
    """
    proposal = """
    接続済みアカウントを使い、投稿カレンダー、定期投稿、月次PDFを納品します。
    連絡はトークルームで非同期に行います。
    """

    verdict = module.evaluate_application(brief, proposal)

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []


def test_interviewer_work_is_not_misclassified_as_being_an_interviewee() -> None:
    module = load_module()
    brief = """
    顧客へのヒアリング質問票を作成し、回答を集計するフォームを構築してください。
    作業と連絡はすべてチャットで完結します。
    """
    proposal = """
    質問票と回答フォームを構築し、集計表と運用手順書を納品します。
    """

    verdict = module.evaluate_application(brief, proposal)

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []


def test_explicitly_absent_live_channels_do_not_reduce_async_work() -> None:
    module = load_module()
    brief = """
    電話・Zoom・面談はありません。連絡はチャットのみです。
    必要に応じて対面打ち合わせが可能な方を歓迎しますが、必須ではありません。
    SNS投稿と月次レポートをお願いします。
    """
    proposal = "投稿運用と月次レポートを非同期で納品します。"

    verdict = module.evaluate_application(brief, proposal)

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []
