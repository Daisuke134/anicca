import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reply_composer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reply_composer", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reply_composer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplyComposerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runner = self.root / "fake_runner.py"
        self.schema = self.root / "schema.json"
        self.schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        self.module = load_module()

    def tearDown(self):
        self.temp.cleanup()

    def write_runner(self, reply_body):
        self.runner.write_text(
            "import json,sys\n"
            "from pathlib import Path\n"
            "args=sys.argv[1:]\n"
            "prompt=sys.stdin.read()\n"
            "assert 'private buyer question' in prompt\n"
            "evidence=Path(args[args.index('--evidence-dir')+1])\n"
            "evidence.mkdir(parents=True,exist_ok=True)\n"
            "result=evidence/'result.json'\n"
            f"result.write_text(json.dumps({{'reply_body':{reply_body!r}}}))\n"
            "(evidence/'summary.json').write_text(json.dumps({'status':'success','result_path':str(result)}))\n",
            encoding="utf-8",
        )

    def write_result_runner(self, reply_body):
        self.runner.write_text(
            "import json,sys\n"
            "from pathlib import Path\n"
            "args=sys.argv[1:]\n"
            "evidence=Path(args[args.index('--evidence-dir')+1])\n"
            "evidence.mkdir(parents=True,exist_ok=True)\n"
            "result=evidence/'result.json'\n"
            f"result.write_text(json.dumps({{'reply_body':{reply_body!r}}}))\n"
            "(evidence/'summary.json').write_text(json.dumps({'status':'success','result_path':str(result)}))\n",
            encoding="utf-8",
        )

    def context(self, last_side="buyer"):
        return {"conversation": [
            {"side": "seller", "body": "earlier answer"},
            {"side": last_side, "body": "private buyer question"},
        ]}

    def test_runner_composer_returns_send_ready_text_and_removes_temp_evidence(self):
        self.write_runner("具体的な回答と次の作業をお送りします。")
        temp_root = self.root / "transient"
        temp_root.mkdir()
        composer = self.module.RunnerComposer(
            runner=self.runner,
            schema=self.schema,
            workdir=self.root,
            temp_root=temp_root,
        )

        body = composer(self.context())

        self.assertEqual(body, "具体的な回答と次の作業をお送りします。")
        self.assertEqual(list(temp_root.iterdir()), [])

    def test_seller_last_is_rejected_before_model_invocation(self):
        self.runner.write_text("raise SystemExit('must not run')\n", encoding="utf-8")
        composer = self.module.RunnerComposer(
            runner=self.runner,
            schema=self.schema,
            workdir=self.root,
            temp_root=self.root,
        )

        with self.assertRaisesRegex(ValueError, "buyer-last"):
            composer(self.context(last_side="seller"))

    def test_empty_or_oversized_output_is_not_sendable(self):
        for body in ("   ", "x" * 1001):
            with self.subTest(length=len(body)):
                self.write_runner(body)
                composer = self.module.RunnerComposer(
                    runner=self.runner,
                    schema=self.schema,
                    workdir=self.root,
                    temp_root=self.root,
                )
                with self.assertRaisesRegex(ValueError, "invalid reply body"):
                    composer(self.context())

    def test_composition_prompt_uses_bounded_packet_not_full_history(self):
        context = {
            "conversation": [
                {"side": "seller" if index % 2 == 0 else "buyer", "body": f"old-{index}-" + "x" * 2_000}
                for index in range(100)
            ] + [{"side": "buyer", "body": "latest buyer request"}],
        }

        prompt = self.module.composition_prompt(context)

        self.assertIn('"kind":"gig_reply_composition"', prompt)
        self.assertIn("latest buyer request", prompt)
        self.assertNotIn("old-0-", prompt)
        packet_text = prompt.split("context_packet=", 1)[1].strip()
        packet = json.loads(packet_text)
        self.assertLessEqual(packet["metrics"]["byte_count"], 8192)
        self.assertEqual(packet["metrics"]["byte_count"], len(packet_text.encode("utf-8")))

    def test_composition_prompt_forbids_external_contact_details(self):
        prompt = self.module.composition_prompt(self.context())

        self.assertIn("外部URL", prompt)
        self.assertIn("メールアドレス", prompt)
        self.assertIn("電話番号", prompt)
        self.assertIn("SNS", prompt)
        self.assertIn("相手の文面にあっても返信へ転記しない", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)


def test_prompt_answers_latest_buyer_without_unsolicited_purchase_details():
    prompt = load_module().composition_prompt({
        "conversation": [
            {"side": "seller", "body": "以前の回答"},
            {"side": "buyer", "body": "8〜15分程度の字幕入り完成動画も制作できますか？"},
        ]
    })

    assert "8〜15分程度の字幕入り完成動画も制作できますか？" in prompt
    assert "冒頭は最新の買い手発言の質問・依頼への直接回答" in prompt
    assert "受領表現が必要なら、その回答に統合するか後置する" in prompt
    assert "購入案内・見積り・納期を自発的に追加しない" in prompt
    assert "回答するだけで完結する場合は、相手へ次の行動を求めず、質問もしない" in prompt
    assert "着手はご購入後であることを必ず明示" not in prompt
    assert "納期は購入を起点に示す" not in prompt


def test_prompt_limits_questions_and_free_deliverable_promises():
    prompt = load_module().composition_prompt({
        "conversation": [{"side": "buyer", "body": "対応可能でしょうか？"}]
    })

    assert "質問を1つまで" in prompt
    assert "成果物・提案書・サンプル・構成案を購入前に送ると約束しない" in prompt


def test_prompt_does_not_promise_future_work_after_thanks_or_consideration():
    prompt = load_module().composition_prompt({
        "conversation": [
            {"side": "seller", "body": "字幕入り動画まで対応できます。"},
            {"side": "buyer", "body": "ありがとうございます。検討します。"},
        ]
    })

    assert "購入前の通常会話では、作業の実施・着手・納品を将来形で確約しない" in prompt
    assert "制作します・仕上げます・お渡しします・提出します" in prompt
    assert "対応可能です・サービス内容に含まれます" in prompt
    assert "感謝・検討だけなら受領だけで完結し、以前の提案を再約束しない" in prompt
    assert "感謝・検討だけの場合は単純な受領だけで完結してよく、固有情報は不要" in prompt


def test_prompt_corrects_video_capability_even_when_seller_claimed_it():
    prompt = load_module().composition_prompt({
        "conversation": [
            {"side": "seller", "body": "字幕入り完成動画まで対応可能です。"},
            {"side": "buyer", "body": "8〜15分の字幕入り完成動画は作れますか？"},
        ]
    })

    assert "動画そのものの編集、字幕・テロップ挿入、映像加工、書き出し、完成動画制作は対応できません" in prompt
    assert "過去のseller発言に誤った対応可能claimがある場合だけ事実を訂正する" in prompt
    assert "購入案内・見積り・代替案を出さず、質問もしない" in prompt
    for body in ("動画の企画と台本だけを作れますか？", "WordPressのページ更新はできますか？",
                 "8〜15分の字幕入り完成動画は作れますか？"):
        prompt = load_module().composition_prompt({"conversation": [{"side": "buyer", "body": body}]})
        assert "動画の企画・台本・文章など編集不要の業務と動画以外（例: WordPress）はこのhard declineに含めず、通常判定する" in prompt
        assert "過去のseller claimがない場合は、訂正と称さず丁寧に辞退する" in prompt


def test_the_prompt_demands_a_definite_yes_or_no():
    # Availability questions need a definite answer; other intents must not get a forced one.
    prompt = load_module().composition_prompt({
        "conversation": [{"side": "buyer", "body": "可能でしょうか？"}]
    })
    assert "可否を尋ねた場合だけ、「可能です」「対応できません」のように可否を断定する" in prompt


def test_prompt_does_not_force_availability_for_thanks_or_price_questions():
    for body in ("ありがとうございます。", "価格を教えてください。"):
        prompt = load_module().composition_prompt({
            "conversation": [{"side": "buyer", "body": body}]
        })
        assert "価格・納期の質問、感謝、確認には不自然な可否表現を付けない" in prompt
        if "価格" in body:
            assert "価格または納期を尋ねた場合だけ" in prompt
            assert "会話内の検証済み条件の範囲" in prompt
            assert "購入を催促しない" in prompt


def test_prompt_does_not_repeat_old_seller_cta_deadline_or_question():
    prompt = load_module().composition_prompt({
        "conversation": [
            {"side": "seller", "body": "ご購入後に開始し、納期は購入から3営業日です。購入されますか？"},
            {"side": "buyer", "body": "8〜15分の動画制作は可能ですか？"},
        ]
    })
    assert "直近のseller発言に購入案内・購入起点の納期・質問があっても" in prompt
    assert "最新の買い手が求めていなければ反復しない" in prompt


def test_the_existing_guards_survive():
    # None of the standing prohibitions may be lost while editing the requirements block.
    prompt = load_module().composition_prompt({
        "conversation": [{"side": "buyer", "body": "お願いします"}]
    })
    for guard in ("外部URL", "1000文字以内", "reply_body", "verified_research"):
        assert guard in prompt, guard


def test_prompt_answers_owned_tiktok_facts_for_incident_and_unfamiliar_paraphrase():
    conversations = (
        "TikTokなどのSNSアカウントは利用できますか？フォロワー数も教えてください。",
        "アプリを紹介できる媒体の規模感と、使える掲載先があれば知りたいです。",
    )

    for buyer_message in conversations:
        prompt = load_module().composition_prompt({
            "conversation": [{"side": "buyer", "body": buyer_message}],
        })

        assert buyer_message in prompt
        assert "TikTok" in prompt
        assert "3,281" in prompt
        assert "今回のPRに利用可能" in prompt
        assert "確認時点では3,281人" in prompt
        assert "現在の人数・最新値・リアルタイムの数としては表現しない" in prompt
        assert "観測時点で確認済みの現在値" not in prompt
        assert "どのSNSか" in prompt
        assert "今回のご依頼に利用できます" in prompt
        assert "本人のprivate account" in prompt
        assert "現在は投稿していない" in prompt
        assert "https://www.tiktok.com/@anicca_buddha" in prompt
        assert "現在は投稿していないため今回のPRに利用可能" in prompt


def test_incident_prompt_requires_every_question_and_uses_verified_application():
    context = {
        "conversation": [{
            "side": "buyer",
            "body": "1日何件ですか？何日かかりますか？応募時の見積りから変更はありますか？",
        }],
        "counterparty_user_id": "6231861",
        "_own_user_path": "/users/9999999",
        "verified_application": {
            "request_id": "5205196",
            "offer_id": "6311743",
            "requester_user_id": "6231861",
            "title": "1700件の作業案件",
            "proposal_body": "応募時の提案本文",
            "price_jpy": 50000,
            "deliver_date": "2026-08-14",
            "offer_url": "https://coconala.com/mypage/offers/6311743",
        },
    }
    prompt = load_module().composition_prompt(context)
    for phrase in (
        "1日何件", "何日", "応募時の見積り", "明示的な質問",
        "黙って省略しない", "未依頼のCTA・見積り・フォローアップ",
        "50000", "2026-08-14",
    ):
        assert phrase in prompt
    assert "9999999" not in prompt
    missing = load_module().composition_prompt({"conversation": [{"side": "buyer", "body": "応募時の価格から変わりましたか？"}]})
    assert "根拠がなければ価格・納期・変更有無を作らない" in missing
    assert "質問を1つまで" in missing
    mismatch = {**context, "counterparty_user_id": "9999999"}
    try:
        load_module().composition_prompt(mismatch)
    except ValueError:
        pass
    else:
        raise AssertionError("composition accepted mismatched application identity")


def test_runner_rejects_price_question_without_verified_price_and_accepts_explicit_unchanged_price():
    module = load_module()
    context = {
        "conversation": [{"side": "buyer", "body": "1日何件ですか？何日かかりますか？応募時の見積りから変更はありますか？"}],
        "counterparty_user_id": "6231861",
        "verified_application": {
            "request_id": "5205196", "offer_id": "6311743", "requester_user_id": "6231861",
            "title": "1700件の作業案件", "proposal_body": "応募時の提案本文", "price_jpy": 50000,
            "deliver_date": "2026-08-14", "offer_url": "https://coconala.com/mypage/offers/6311743",
        },
    }
    test = ReplyComposerTest("runTest")
    test.setUp()
    try:
        test.write_result_runner("1日200件、9日で完了する見込みです。")
        composer = module.RunnerComposer(runner=test.runner, schema=test.schema, workdir=test.root, temp_root=test.root)
        try:
            composer(context)
        except ValueError as error:
            assert str(error) == "reply omitted verified application price"
        else:
            raise AssertionError("price omission was sent")
        test.write_result_runner("1日200件、9日で完了する見込みです。応募時の50,000円から変更ありません。")
        assert composer(context).endswith("変更ありません。")
    finally:
        test.tearDown()


def test_runner_rejects_partial_answers_to_daily_capacity_and_duration_questions():
    module = load_module()
    context = {
        "conversation": [{"side": "buyer", "body": "1日あたり何件できますか？何日かかりますか？"}],
    }
    test = ReplyComposerTest("runTest")
    test.setUp()
    try:
        composer = module.RunnerComposer(
            runner=test.runner, schema=test.schema, workdir=test.root, temp_root=test.root,
        )
        for incomplete, reason in (
            ("期限内に対応できます。", "reply omitted daily capacity"),
            ("1日200件ほど対応できます。", "reply omitted completion duration"),
            ("1日200件ほど、8月14日です。", "reply omitted completion duration"),
        ):
            test.write_result_runner(incomplete)
            try:
                composer(context)
            except ValueError as error:
                assert str(error) == reason
            else:
                raise AssertionError(f"partial answer was accepted: {incomplete}")
        test.write_result_runner("1日200件ほど、9日で完了する見込みです。")
        assert composer(context).startswith("1日200件")
    finally:
        test.tearDown()


def test_answer_guards_cover_natural_capacity_duration_phrasing_and_reject_nonanswers():
    module = load_module()
    for latest, body, reason in (
        ("1日で対応可能な数を教えてください。", "対応可能です。", "reply omitted daily capacity"),
        ("一日何件対応できますか？", "対応可能です。", "reply omitted daily capacity"),
        ("完了までどれくらいかかりますか？", "確認しました。", "reply omitted completion duration"),
        ("納品までどれくらいかかりますか？", "確認しました。", "reply omitted completion duration"),
        ("何日かかりますか？", "納期は14日です。", "reply omitted completion duration"),
    ):
        with __import__("pytest").raises(ValueError, match=reason):
            module._require_verified_application_terms(
                {"conversation": [{"side": "buyer", "body": latest}]}, body,
            )


def test_change_answer_rejects_hedges_questions_and_external_contacts():
    module = load_module()
    context = {
        "conversation": [{"side": "buyer", "body": "応募時の見積りから変更はありますか？"}],
        "verified_application": {"price_jpy": 50000},
    }
    for body in (
        "応募時の50,000円から変更はないとは言えません。",
        "応募時の50,000円から変更ありませんか？",
        "応募時の50,000円から変更はないですか？",
        "応募時の50,000円から変更はありませんよね？",
        "応募時の50,000円から変更はない可能性があります。",
        "応募時の50,000円から変更はないと思います。",
        "応募時の50,000円から変更ありません。foo@example.comへご連絡ください。",
        "応募時の50,000円から変更ありません。https://evil.example をご覧ください。",
        "応募時の50,000円から変更ありません。HTTPS://evil.example をご覧ください。",
        "応募時の50,000円から変更ありません。www.evil.example をご覧ください。",
        "応募時の50,000円から変更ありません。evil.example をご覧ください。",
        "応募時の50,000円から変更ありません。foo＠example.comへご連絡ください。",
    ):
        with __import__("pytest").raises(ValueError):
            module._require_verified_application_terms(context, body)
    for normal in ("対応環境はバージョン 1.2 です。", "成果物は data.csv です。"):
        module._require_verified_application_terms(
            {"conversation": [{"side": "buyer", "body": "形式を教えてください。"}]}, normal,
        )


def test_external_contact_guard_rejects_bare_handles_but_allows_at_price_notation():
    module = load_module()
    context = {"conversation": [{"side": "buyer", "body": "形式を教えてください。"}]}
    for body in (
        "TikTokは@anicca_buddhaです。",
        "TikTokは＠anicca_buddhaです。",
        "TikTokは@anicca.jpです。",
        "TikTokは@anicca-buddhaです。",
        "TikTokは@12345です。",
        "TikTokは@anicca.です。",
        "TikTokは@anicca.jp.です。",
    ):
        with __import__("pytest").raises(ValueError, match="external contact"):
            module._require_verified_application_terms(context, body)
    for body in (
        "費用は@500円です。",
        "費用は＠５００円です。",
        "費用は@5,000円です。",
        "費用は＠５，０００円です。",
    ):
        module._require_verified_application_terms(context, body)


def test_external_contact_guard_allows_only_the_verified_private_tiktok_url():
    module = load_module()
    context = {"conversation": [{"side": "buyer", "body": "利用できるアカウントを教えてください。"}]}
    module._require_verified_application_terms(
        context,
        "私個人のアカウントで、現在投稿していないため今回のPRに利用できます。"
        "https://www.tiktok.com/@anicca_buddha",
    )
    for body in (
        "https://www.tiktok.com/@anicca.jp",
        "https://www.tiktok.com/@anicca_buddha/extra",
        "https://www.tiktok.com/@anicca_buddha?x=1",
        "https://evil.example/@anicca_buddha",
    ):
        with __import__("pytest").raises(ValueError, match="external contact"):
            module._require_verified_application_terms(context, body)


def test_price_intent_layers_agree_and_capacity_requires_per_day_relation():
    module = load_module()
    with __import__("pytest").raises(ValueError, match="reply omitted verified application price"):
        module._require_verified_application_terms({
            "conversation": [{"side": "buyer", "body": "応募時の価格について伺いたいです。"}],
            "verified_application": {"price_jpy": 50000},
        }, "確認しました。")
    with __import__("pytest").raises(ValueError, match="reply omitted daily capacity"):
        module._require_verified_application_terms({
            "conversation": [{"side": "buyer", "body": "1日あたり何件できますか？"}],
        }, "1日後に200件を確認します。")
    with __import__("pytest").raises(ValueError, match="change status"):
        module._require_verified_application_terms({
            "conversation": [{"side": "buyer", "body": "応募時の見積りから変更はありますか？"}],
            "verified_application": {"price_jpy": 50000},
        }, "応募時の50,000円から変更はありませんが、変更があります。")


def test_missing_official_price_and_non_url_contacts_fail_closed():
    module = load_module()
    with __import__("pytest").raises(ValueError, match="unverified price"):
        module._require_verified_application_terms({
            "conversation": [{"side": "buyer", "body": "価格を教えてください。"}],
        }, "価格は99,999円です。")
    module._require_verified_application_terms({
        "conversation": [{"side": "buyer", "body": "価格を教えてください。"}],
    }, "正確な価格を確認させてください。")
    for body in ("電話番号は090-1234-5678です。", "LINE IDはbuyer_supportです。"):
        with __import__("pytest").raises(ValueError, match="external contact"):
            module._require_verified_application_terms({
                "conversation": [{"side": "buyer", "body": "連絡方法を教えてください。"}],
            }, body)


def test_delivery_only_change_question_does_not_trigger_price_guard():
    module = load_module()
    module._require_verified_application_terms({
        "conversation": [{"side": "buyer", "body": "納期を変更できますか？"}],
        "verified_application": {"price_jpy": 50000},
    }, "納期は変更できます。")


def test_price_guard_ignores_gratitude_and_accepts_exact_japanese_man_yen_only():
    module = load_module()
    application = {"price_jpy": 50000}
    module._require_verified_application_terms({
        "conversation": [{"side": "buyer", "body": "お見積りありがとうございます"}],
        "verified_application": application,
    }, "ありがとうございます。")
    module._require_verified_application_terms({
        "conversation": [{"side": "buyer", "body": "応募時の見積りから変更はありますか？"}],
        "verified_application": application,
    }, "応募時の5万円から変更ありません。")
    try:
        module._require_verified_application_terms({
            "conversation": [{"side": "buyer", "body": "応募時の見積りから変更はありますか？"}],
            "verified_application": application,
        }, "応募時の4万円から変更ありません。")
    except ValueError as error:
        assert str(error) == "reply omitted verified application price"
    else:
        raise AssertionError("different Japanese man-yen price was accepted")


def test_change_price_guard_requires_yen_and_same_sentence_disposition():
    module = load_module()
    context = {"conversation": [{"side": "buyer", "body": "応募時の見積りから変更はありますか？"}], "verified_application": {"price_jpy": 50000}}
    for body in (
        "応募時の50000から変更ありません。",
        "応募時の50,000円です。変更ありません。",
        "応募時の40,000円から変更ありません。",
        "応募時の50,000円です。価格は変わりません。",
    ):
        with __import__("pytest").raises(ValueError, match="reply omitted verified application"):
            module._require_verified_application_terms(context, body)
    module._require_verified_application_terms(context, "応募時の50,000円から変更ありません。")
    module._require_verified_application_terms(context, "応募時から変更はなく、50,000円です。")
    module._require_verified_application_terms(
        {"conversation": [{"side": "buyer", "body": "価格を教えてください"}], "verified_application": {"price_jpy": 50000}},
        "価格は50,000円です。",
    )
