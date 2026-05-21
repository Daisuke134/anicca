# EDSL Synthetic User Simulation 仕様書

## 1. 概要

### 目的
Expected Parrot (EDSL) を使用して、合成ユーザー（Synthetic User）をシミュレーションし、各ペルソナに最適な通知文言を事前に特定する。これにより、ユーザーごとにパーソナライズされた行動介入（Nudge）を実現する。

### アプローチの特徴
- **オフラインシミュレーション**: 事前にペルソナ × 通知の効果をシミュレーション
- **静的マッピング**: シミュレーション結果をJSONとして保持
- **ペルソナマッチング**: オンボーディングでユーザーを既存ペルソナに分類
- **ABテスト検証**: シミュレーション vs ランダム で効果を比較

### Contextual Banditを使わない理由
- シンプルさ優先
- まずシミュレーションの精度を検証したい
- オンライン学習の複雑さを避ける
- 将来的にBanditへの移行も可能

---

## 2. アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: オフラインシミュレーション                          │
│                                                             │
│  [ペルソナ定義] × [通知文言候補]                             │
│         ↓                                                   │
│  [EDSL シミュレーション実行]                                 │
│         ↓                                                   │
│  [ペルソナ別 通知効果マッピング]                             │
│         ↓                                                   │
│  persona_notification_map.json として保存                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: オンボーディング                                    │
│                                                             │
│  [ユーザーの回答]                                            │
│    - 理想タグ（早起き、筋トレ etc）                          │
│    - Strugglesタグ（夜更かし、三日坊主 etc）                 │
│    - 性格傾向                                                │
│         ↓                                                   │
│  [ペルソナ判定ロジック]                                      │
│         ↓                                                   │
│  user.persona_type = "perfectionist" etc                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: 通知送信                                            │
│                                                             │
│  [通知タイミング到来]                                        │
│         ↓                                                   │
│  persona_notification_map[user.persona_type] から選択       │
│         ↓                                                   │
│  [通知送信] + [Mixpanelログ]                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: 効果検証（ABテスト）                                │
│                                                             │
│  A群: シミュレーションTOP3から選択                          │
│  B群: ランダム選択                                          │
│         ↓                                                   │
│  [効果測定]                                                  │
│    - 通知タップ率                                            │
│    - 目標達成率（就寝、起床、運動）                          │
│    - 継続率                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. ペルソナ定義

### 3.1 ペルソナタイプ一覧

| ID | ペルソナ名 | 特徴 | 典型的なStruggles |
|----|-----------|------|-------------------|
| `perfectionist` | 完璧主義型 | 高い目標を持つが、達成できないと自己嫌悪 | 夜更かし、自己嫌悪 |
| `procrastinator` | 先延ばし型 | やるべきことから逃げる傾向 | 夜更かし、三日坊主 |
| `free_spirit` | 自由人型 | 自律が苦手、ルールに縛られたくない | 不規則な生活 |
| `anxious` | 不安型 | 心配性で眠れない、考えすぎる | 不眠、反芻思考 |
| `overworker` | 頑張りすぎ型 | 仕事を優先しすぎる | 睡眠不足、運動不足 |
| `social_media_addict` | SNS依存型 | スマホを手放せない | 夜更かし、スクリーンタイム |

### 3.2 ペルソナの詳細定義（EDSL Agent用）

```python
PERSONAS = {
    "perfectionist": {
        "age_range": [25, 35],
        "personality": "完璧主義だけど続かない",
        "sleep_time": "深夜1-2時",
        "pain_points": [
            "自分との約束を守れない",
            "高い目標を立てるが達成できない",
            "失敗すると自己嫌悪に陥る"
        ],
        "past_failures": ["習慣トラッカー5個試して全部やめた"],
        "motivation_style": "自己成長、自己実現",
        "response_to_criticism": "ギクッとする、内省する"
    },
    "procrastinator": {
        "age_range": [20, 30],
        "personality": "締め切りギリギリタイプ",
        "sleep_time": "深夜2-3時",
        "pain_points": [
            "やるべきことから逃げてしまう",
            "明日やろうが口癖",
            "気づいたら時間が過ぎている"
        ],
        "past_failures": ["何度も早起きを決意したが3日で終わる"],
        "motivation_style": "締め切り駆動",
        "response_to_criticism": "分かってるけどできない"
    },
    # ... 他のペルソナも同様に定義
}
```

---

## 4. 通知文言候補

### 4.1 就寝ドメイン（Bedtime）

| ID | 文言 | BCT（行動変容技法） | 想定ペルソナ |
|----|------|---------------------|-------------|
| B01 | どうせ夜更かししたって今日は取り戻せない。もう寝よう。 | 結果の再評価 | procrastinator |
| B02 | また明日の自分に借金するの？ | 未来の自己との対話 | perfectionist |
| B03 | 今夜も自分との約束を破るんだ。 | 自己契約 | perfectionist |
| B04 | この1時間で何が変わる？本当に必要？ | 認知的再構成 | overworker |
| B05 | 睡眠不足は脳を酔っ払い状態にする。明日のパフォーマンス大丈夫？ | 科学的根拠 | overworker |
| B06 | スマホを見てる間に、体は休息を求めて悲鳴を上げてる。 | 身体感覚への注意 | social_media_addict |
| B07 | 明日の自分は今日より疲れてる。今やらないなら明日もやらない。 | 現実的思考 | procrastinator |
| B08 | いつまでこのパターンを繰り返すの？ | パターン認識 | all |
| B09 | 寝ることは諦めじゃない。明日への投資。 | リフレーミング | perfectionist |
| B10 | 今日できなかったことは、睡眠不足の明日にはもっとできない。 | 論理的帰結 | procrastinator |
| B11 | この夜更かし、本当に楽しんでる？それとも逃げてる？ | 自己洞察 | procrastinator |
| B12 | 1時間後の後悔より、今すぐの行動。 | 即時vs遅延報酬 | all |
| B13 | 自分を大事にするって、こういう瞬間に決まる。 | 自己慈悲 | anxious |
| B14 | 疲れてるのにスマホ見てるのは、脳がハイジャックされてるだけ。 | 認知バイアス指摘 | social_media_addict |
| B15 | 寝る時間を守れる人は、人生をコントロールできる人。 | アイデンティティ | perfectionist |
| B16 | 今日1日を振り返ってみて。十分頑張った。休んでいい。 | 肯定・許可 | overworker |
| B17 | あと5分、あと10分...気づいたら1時間。そのパターン知ってるよね。 | パターン認識 | social_media_addict |
| B18 | 明日の朝、スッキリ起きた自分を想像してみて。 | 未来イメージング | all |
| B19 | 今の選択が、1週間後の自分を作る。 | 長期的視点 | all |
| B20 | 睡眠は最強の自己投資。ROI無限大。 | 投資フレーム | overworker |

### 4.2 起床ドメイン（Wake）

| ID | 文言 | BCT | 想定ペルソナ |
|----|------|-----|-------------|
| W01 | 二度寝の10分より、起きた後のコーヒーの10分の方が価値がある。 | 価値比較 | all |
| W02 | 今起きれば、昨日より1日長く生きられる。 | 人生視点 | perfectionist |
| W03 | ベッドの中にいる限り、何も始まらない。 | 行動の必要性 | procrastinator |
| W04 | 起きた瞬間が一番つらい。でも5分後には忘れてる。 | 一時性の認識 | all |
| W05 | 今日という日は二度と来ない。 | 希少性 | all |
| W06 | 昨日の夜、朝起きようって決めたよね。覚えてる？ | 自己契約想起 | perfectionist |
| W07 | このまま寝てたら、また夜に後悔する。そのループ、断ち切ろう。 | パターン断絶 | procrastinator |
| W08 | 体は起きたがってる。脳がサボってるだけ。 | 身体vs認知 | all |
| W09 | 1日の質は、最初の1時間で決まる。 | 初動の重要性 | overworker |
| W10 | 二度寝した後のダルさ、知ってるでしょ。 | 経験想起 | all |

### 4.3 運動ドメイン（Movement）

| ID | 文言 | BCT | 想定ペルソナ |
|----|------|-----|-------------|
| M01 | 行く前は面倒。行った後は最高。毎回そうでしょ。 | 経験想起 | all |
| M02 | 体を動かさない日は、脳も動かない。 | 心身連動 | overworker |
| M03 | 10分でいい。10分だけ動いてみて。 | ミニマルコミット | procrastinator |
| M04 | 座ってる時間が長いほど、寿命が縮む。これ、科学的事実。 | 科学的根拠 | all |
| M05 | 1年後の体は、今日の選択でできている。 | 長期視点 | perfectionist |

---

## 5. EDSLシミュレーション手順

### 5.1 環境セットアップ

```bash
# EDSLインストール
pip install edsl

# Expected Parrotアカウント作成（無料$25クレジット付き）
# https://expectedparrot.com/login
```

### 5.2 シミュレーションコード

```python
from edsl import QuestionLinearScale, QuestionFreeText, Agent, AgentList, Survey
from collections import defaultdict
import json

# ペルソナ定義
def create_agents_for_persona(persona_id: str, count: int = 10) -> AgentList:
    """指定ペルソナのAgentを複数生成"""
    persona = PERSONAS[persona_id]
    agents = []
    
    for i in range(count):
        age = random.randint(*persona["age_range"])
        agent = Agent(traits={
            "persona_type": persona_id,
            "age": age,
            "personality": persona["personality"],
            "typical_sleep_time": persona["sleep_time"],
            "pain_points": ", ".join(persona["pain_points"]),
            "past_failures": ", ".join(persona["past_failures"]),
            "motivation_style": persona["motivation_style"]
        })
        agents.append(agent)
    
    return AgentList(agents)

# 通知効果を評価する質問
def create_notification_question(notification: str, domain: str) -> QuestionLinearScale:
    context = {
        "bedtime": "深夜2時にスマホを見ています",
        "wake": "朝7時、目覚ましが鳴りましたがベッドの中にいます",
        "movement": "仕事中、3時間座りっぱなしです"
    }
    
    return QuestionLinearScale(
        question_name="effectiveness",
        question_text=f"""
あなたは{context[domain]}。
この通知が来ました:

「{notification}」

この通知を見たら、行動を変えようと思いますか？
（就寝ならスマホを置いて寝る、起床なら起き上がる、運動なら立ち上がって動く）
""",
        question_options=[1, 2, 3, 4, 5],
        option_labels={
            1: "全く思わない",
            2: "あまり思わない", 
            3: "どちらとも言えない",
            4: "まあまあ思う",
            5: "すぐ行動する"
        }
    )

# シミュレーション実行
def run_simulation(persona_id: str, notifications: list, domain: str) -> dict:
    """指定ペルソナに対して全通知を評価"""
    agents = create_agents_for_persona(persona_id, count=10)
    results = {}
    
    for notification in notifications:
        q = create_notification_question(notification["text"], domain)
        response = q.by(agents).run()
        
        scores = [r["answer"]["effectiveness"] for r in response.to_list()]
        avg_score = sum(scores) / len(scores)
        
        results[notification["id"]] = {
            "text": notification["text"],
            "avg_score": avg_score,
            "scores": scores
        }
    
    return results

# 全ペルソナ × 全通知でシミュレーション
def run_full_simulation():
    all_results = {}
    
    for persona_id in PERSONAS.keys():
        all_results[persona_id] = {}
        
        for domain, notifications in NOTIFICATIONS.items():
            domain_results = run_simulation(persona_id, notifications, domain)
            
            # TOP5を抽出
            sorted_results = sorted(
                domain_results.items(),
                key=lambda x: x[1]["avg_score"],
                reverse=True
            )[:5]
            
            all_results[persona_id][domain] = [
                {"id": r[0], "text": r[1]["text"], "score": r[1]["avg_score"]}
                for r in sorted_results
            ]
    
    return all_results

# 実行 & 保存
if __name__ == "__main__":
    results = run_full_simulation()
    
    with open("persona_notification_map.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("シミュレーション完了！")
```

### 5.3 出力例（persona_notification_map.json）

```json
{
  "perfectionist": {
    "bedtime": [
      {"id": "B03", "text": "今夜も自分との約束を破るんだ。", "score": 4.6},
      {"id": "B02", "text": "また明日の自分に借金するの？", "score": 4.4},
      {"id": "B15", "text": "寝る時間を守れる人は、人生をコントロールできる人。", "score": 4.3}
    ],
    "wake": [
      {"id": "W06", "text": "昨日の夜、朝起きようって決めたよね。覚えてる？", "score": 4.5},
      {"id": "W02", "text": "今起きれば、昨日より1日長く生きられる。", "score": 4.2}
    ]
  },
  "procrastinator": {
    "bedtime": [
      {"id": "B07", "text": "明日の自分は今日より疲れてる。今やらないなら明日もやらない。", "score": 4.3},
      {"id": "B11", "text": "この夜更かし、本当に楽しんでる？それとも逃げてる？", "score": 4.2}
    ]
  }
}
```

---

## 6. ペルソナ判定ロジック

### 6.1 オンボーディングでの質問

現在のオンボーディングで取得している情報:
- 理想タグ（Ideals）
- Strugglesタグ
- 習慣選択（起床、就寝、トレーニング）

### 6.2 ペルソナ判定マッピング

```swift
// PersonaClassifier.swift

enum PersonaType: String, Codable {
    case perfectionist
    case procrastinator
    case freeSpirit = "free_spirit"
    case anxious
    case overworker
    case socialMediaAddict = "social_media_addict"
    case general  // どれにも当てはまらない場合
}

struct PersonaClassifier {
    
    static func classify(
        ideals: Set<IdealTag>,
        struggles: Set<StruggleTag>
    ) -> PersonaType {
        
        // スコアリング
        var scores: [PersonaType: Int] = [:]
        
        // Perfectionist判定
        if struggles.contains(.selfLoathing) || 
           struggles.contains(.cantKeepPromises) {
            scores[.perfectionist, default: 0] += 2
        }
        if ideals.contains(.disciplined) || ideals.contains(.earlyRiser) {
            scores[.perfectionist, default: 0] += 1
        }
        
        // Procrastinator判定
        if struggles.contains(.procrastination) ||
           struggles.contains(.lateNight) {
            scores[.procrastinator, default: 0] += 2
        }
        
        // Overworker判定
        if struggles.contains(.overwork) ||
           struggles.contains(.noExercise) {
            scores[.overworker, default: 0] += 2
        }
        if ideals.contains(.productive) {
            scores[.overworker, default: 0] += 1
        }
        
        // Anxious判定
        if struggles.contains(.anxiety) ||
           struggles.contains(.rumination) ||
           struggles.contains(.cantSleep) {
            scores[.anxious, default: 0] += 2
        }
        
        // Social Media Addict判定
        if struggles.contains(.phoneDependency) ||
           struggles.contains(.snsAddiction) {
            scores[.socialMediaAddict, default: 0] += 2
        }
        
        // 最高スコアのペルソナを返す
        if let maxScore = scores.max(by: { $0.value < $1.value }),
           maxScore.value >= 2 {
            return maxScore.key
        }
        
        return .general
    }
}
```

### 6.3 ユーザープロファイルへの保存

```swift
// UserProfile.swift に追加

struct UserProfile: Codable {
    // 既存フィールド...
    
    var personaType: PersonaType?
}

// オンボーディング完了時に判定
func completeOnboarding() {
    let persona = PersonaClassifier.classify(
        ideals: selectedIdeals,
        struggles: selectedStruggles
    )
    
    appState.userProfile?.personaType = persona
    appState.updateUserProfile(appState.userProfile!, sync: true)
}
```

---

## 7. 通知選択ロジック

### 7.1 マッピングデータの読み込み

```swift
// PersonaNotificationMap.swift

struct NotificationOption: Codable {
    let id: String
    let text: String
    let score: Double
}

struct PersonaNotificationMap {
    static let shared = PersonaNotificationMap()
    
    private var map: [String: [String: [NotificationOption]]] = [:]
    
    init() {
        // persona_notification_map.json を読み込み
        if let url = Bundle.main.url(forResource: "persona_notification_map", withExtension: "json"),
           let data = try? Data(contentsOf: url),
           let decoded = try? JSONDecoder().decode([String: [String: [NotificationOption]]].self, from: data) {
            self.map = decoded
        }
    }
    
    func getNotifications(for persona: PersonaType, domain: String) -> [NotificationOption] {
        return map[persona.rawValue]?[domain] ?? map["general"]?[domain] ?? []
    }
}
```

### 7.2 通知文言の選択

```swift
// NotificationContentBuilder.swift

struct NotificationContentBuilder {
    
    static func buildContent(
        for habit: HabitType,
        persona: PersonaType,
        isABTestGroupA: Bool
    ) -> String {
        
        let domain = habit.notificationDomain  // "bedtime", "wake", "movement"
        
        if isABTestGroupA {
            // A群: シミュレーションTOP3からランダム選択
            let options = PersonaNotificationMap.shared.getNotifications(
                for: persona,
                domain: domain
            )
            let top3 = Array(options.prefix(3))
            return top3.randomElement()?.text ?? defaultMessage(for: habit)
        } else {
            // B群: デフォルトメッセージ
            return defaultMessage(for: habit)
        }
    }
    
    private static func defaultMessage(for habit: HabitType) -> String {
        switch habit {
        case .wake: return "おはようございます。起きる時間です。"
        case .bedtime: return "そろそろ寝る時間です。"
        case .training: return "トレーニングの時間です。"
        }
    }
}
```

---

## 8. ABテスト設計

### 8.1 グループ分け

```swift
// ABTestManager.swift

enum ABTestGroup: String {
    case groupA = "simulation"  // シミュレーション通知
    case groupB = "control"     // デフォルト通知
}

struct ABTestManager {
    static let shared = ABTestManager()
    
    private let groupKey = "ab_test_notification_group"
    
    var currentGroup: ABTestGroup {
        if let saved = UserDefaults.standard.string(forKey: groupKey),
           let group = ABTestGroup(rawValue: saved) {
            return group
        }
        
        // 初回は50:50でランダム割り当て
        let group: ABTestGroup = Bool.random() ? .groupA : .groupB
        UserDefaults.standard.set(group.rawValue, forKey: groupKey)
        return group
    }
    
    var isSimulationGroup: Bool {
        currentGroup == .groupA
    }
}
```

### 8.2 Mixpanelトラッキング

```swift
// AnalyticsManager.swift に追加

extension AnalyticsManager {
    
    func trackNotificationSent(
        notificationId: String,
        notificationText: String,
        personaType: String,
        domain: String,
        abGroup: String
    ) {
        track("notification_sent", properties: [
            "notification_id": notificationId,
            "notification_text": notificationText,
            "persona_type": personaType,
            "domain": domain,
            "ab_group": abGroup
        ])
    }
    
    func trackNotificationTapped(
        notificationId: String,
        personaType: String,
        domain: String,
        abGroup: String
    ) {
        track("notification_tapped", properties: [
            "notification_id": notificationId,
            "persona_type": personaType,
            "domain": domain,
            "ab_group": abGroup
        ])
    }
    
    func trackGoalAchieved(
        domain: String,
        notificationId: String?,
        personaType: String,
        abGroup: String,
        targetTime: Date,
        actualTime: Date
    ) {
        let timeDiff = actualTime.timeIntervalSince(targetTime) / 60  // 分
        
        track("goal_achieved", properties: [
            "domain": domain,
            "notification_id": notificationId ?? "none",
            "persona_type": personaType,
            "ab_group": abGroup,
            "time_difference_minutes": timeDiff,
            "within_target": timeDiff <= 30
        ])
    }
}
```

### 8.3 評価指標

| 指標 | 計算方法 | 成功基準 |
|------|----------|----------|
| 通知タップ率 | タップ数 / 送信数 | A群 > B群 |
| 目標達成率 | 目標時刻±30分以内 / 送信日数 | A群 > B群 |
| 7日継続率 | 7日間連続で目標達成したユーザー割合 | A群 > B群 |

---

## 9. 実装ステップ

### Phase 1: シミュレーション実行（1-2日）

1. [ ] EDSLインストール & Expected Parrotアカウント作成
2. [ ] ペルソナ6タイプの詳細定義
3. [ ] 通知文言20個（各ドメイン）の作成
4. [ ] シミュレーションスクリプト実行
5. [ ] `persona_notification_map.json` 生成
6. [ ] TOP10コンテンツ作成（ショート動画用）

### Phase 2: アプリ実装（2-3日）

1. [ ] `PersonaType` enum追加
2. [ ] `PersonaClassifier` 実装
3. [ ] オンボーディング完了時にペルソナ判定追加
4. [ ] `persona_notification_map.json` をBundleに追加
5. [ ] `PersonaNotificationMap` 実装
6. [ ] `NotificationContentBuilder` 修正
7. [ ] `ABTestManager` 実装
8. [ ] Mixpanelイベント追加

### Phase 3: 効果検証（1-2週間）

1. [ ] ABテスト開始
2. [ ] 1週間後にデータ確認
3. [ ] A群 vs B群 の比較分析
4. [ ] シミュレーション精度の評価
5. [ ] 必要に応じてペルソナ定義・通知文言を修正

---

## 10. 将来の拡張

### 10.1 シミュレーション精度の向上
- 実際のユーザー行動データをEDSLのペルソナ定義に反映
- 効果が低かった通知を除外、高かった通知を追加

### 10.2 リアルタイム最適化への移行
- 十分なデータが溜まったらContextual Banditへ移行
- オンライン学習による個人最適化

### 10.3 ドメイン拡張
- メンタル（自己嫌悪、不安）への対応
- 習慣フォローアップへの対応

---

## 付録: コンテンツ活用

### A.1 ショート動画「AI1000人に聞いた」シリーズ

シミュレーション結果を使ったコンテンツ:

1. **「AI1000人に聞いた 夜更かしをやめさせる通知 TOP10」**
   - シミュレーションTOP10を動画化
   - AIのコメントをポップアップ表示
   - CTA: 「この通知試すなら → Anicca」

2. **「三日坊主のクローン1000人に聞いた 朝起きられる声かけ TOP10」**
   - procrastinatorペルソナのシミュレーション結果

3. **カルーセル版**
   - 1位〜10位をカードで表示
   - 量産可能なフォーマット

### A.2 コンテンツ → 機能への反映

バズったコンテンツの通知文言を実際のアプリに実装:
1. エンゲージメント高い文言を特定
2. `persona_notification_map.json` に追加
3. 次回シミュレーションで効果検証


