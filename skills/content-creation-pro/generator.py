"""
Content Creation Pro - Multi-platform Content Generator
Integrated from: content-writer, social-media-content-calendar, social-media-content, xhs-content
"""

import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ─────────────────────────────────────────────
# Platform Configs
# ─────────────────────────────────────────────

PLATFORM_SPECS = {
    "xiaohongshu": {
        "emoji": "📕",
        "word_range": (300, 800),
        "tags_count": 15,
        "format": "post",
        "best_days": ["周二", "周四", "周六", "周日"],
        "best_hours": [10, 12, 19, 21],
    },
    "zhihu": {
        "emoji": "🧠",
        "word_range": (1000, 2000),
        "tags_count": 5,
        "format": "answer",
        "best_days": ["周二", "周三", "周四"],
        "best_hours": [8, 10, 12],
    },
    "douyin": {
        "emoji": "🎵",
        "word_range": (200, 500),
        "tags_count": 5,
        "format": "script",
        "duration_sec": (60, 120),
        "best_days": ["周二", "周三", "周四"],
        "best_hours": [19, 20, 21],
    },
    "wechat": {
        "emoji": "📰",
        "word_range": (1500, 3000),
        "tags_count": 3,
        "format": "article",
        "best_days": ["周二", "周三", "周四"],
        "best_hours": [12, 20],
    },
}

# Content mix ratio for scheduling
CONTENT_MIX = {
    "educational": 0.40,
    "engaging": 0.25,
    "promotional": 0.20,
    "personal": 0.15,
}

# ─────────────────────────────────────────────
# Template Renderers
# ─────────────────────────────────────────────

def render_xiaohongshu(topic: str, angle: str, style: str = "casual") -> Dict:
    """Render Xiaohongshu post with hooks, body, tags."""
    emoji = "💡" if style == "educational" else "🔥" if style == "viral" else "✨"
    headline = f"{emoji} {topic}"
    hook = f"说实话，我一开始也不信这个方法有用，直到试了才发现……"
    body_paras = [
        f"最近很多人在问「{topic}」这个问题，我研究了一下，发现其实没那么难。",
        f"核心在于找准角度：{angle}",
        "第一步，先搞清楚自己的目标人群是谁；第二步，针对他们的痛点组织内容。",
        "说实话，这个方法对我帮助很大，效率提升不止一点点。",
        "如果你也在做类似的内容，这条可以先收藏。",
    ]
    tags = _generate_tags(topic, platform="xiaohongshu")
    return {
        "platform": "xiaohongshu",
        "headline": headline,
        "hook": hook,
        "body": "\n\n".join(body_paras),
        "tags": tags,
        "image_prompts": [
            "封面图：标题大字+情绪氛围，暖色调",
            "内容图：步骤截图或对比图，信息密度高",
            "结尾图：结论总结+收藏引导",
        ],
    }


def render_zhihu(question: str, topic: str, angle: str) -> Dict:
    """Render Zhihu answer with authority structure."""
    hook = f"作为深度研究过「{topic}」的人，我来系统回答这个问题。"
    body_paras = [
        f"首先直接回答：{question}",
        f"展开来说，这里面有几个关键点需要说明：",
        f"1. 核心原理：{angle}",
        "2. 实践方法：需要分步骤来操作",
        "3. 注意事项：避免常见的误区",
        "总结一下：找准方向+持续投入=结果。",
    ]
    tags = _generate_tags(topic, platform="zhihu")
    return {
        "platform": "zhihu",
        "headline": question,
        "hook": hook,
        "body": "\n\n".join(body_paras),
        "tags": tags,
        "cta": "如果对你有帮助，欢迎点赞关注，我会持续输出实用内容。",
    }


def render_douyin(topic: str, angle: str) -> Dict:
    """Render Douyin script with hook, body, CTA."""
    hook = f"如果你也在为「{topic}」发愁，这个方法一定要试试！"
    body = [
        "先说结论：这个方法真的管用。",
        f"核心技巧就一个：{angle}",
        "第一步，打开工具；第二步，按这个思路操作；第三步，坐等效果。",
        "真的没你想的那么复杂，看完你就会了！",
    ]
    tags = _generate_tags(topic, platform="douyin")
    return {
        "platform": "douyin",
        "duration_est": "60-90秒",
        "hook": f"【开场钩子】前3秒：{hook}",
        "body": "\n".join(body),
        "cta": "觉得有用就点赞收藏，还有什么问题评论区见！",
        "caption": f"{topic} | {angle} #教程 #干货",
        "tags": tags,
    }


def render_wechat(topic: str, angle: str, style: str = "professional") -> Dict:
    """Render WeChat official account article."""
    subheads = ["背景与痛点", "核心方法", "实操步骤", "效果与总结"]
    paras = [
        f"你是否有这样的困扰：{topic}，却不知道从何下手？\n\n本文将系统解答这个问题。",
        f"\n## {subheads[0]}\n\n很多人卡在{angle}这一步，主要是因为没有找到正确的方法。",
        f"\n## {subheads[1]}\n\n核心在于三个要点：目标明确、步骤清晰、持续执行。",
        f"\n## {subheads[2]}\n\n第一步，做好规划；第二步，按计划执行；第三步，定期复盘优化。",
        f"\n## {subheads[3]}\n\n坚持下来，效果会让你惊喜。如果觉得有帮助，欢迎转发关注！",
    ]
    tags = _generate_tags(topic, platform="wechat")
    return {
        "platform": "wechat",
        "headline": f"「{topic}」最全攻略｜附实操指南",
        "body": "".join(paras),
        "tags": tags,
        "cta": "欢迎转发给需要的朋友，点击在看支持一下！",
    }


def _generate_tags(topic: str, platform: str) -> List[str]:
    """Generate hashtags for a topic on given platform."""
    base = topic.replace(" ", "").replace("AI", "AI人工智能")
    if platform == "xiaohongshu":
        return [
            f"#{base}", "#内容创作", "#自媒体干货",
            "#职场成长", "#副业变现", "#AI工具",
            "#小红书运营", "#干货分享", "#打工人必看",
            "#效率提升", "#笔记技巧", "#内容日历",
            "#原创内容", "#写作技巧", "#涨粉攻略",
        ]
    elif platform == "douyin":
        return [f"#{base}", "#教程", "#干货", "#职场", "#成长"]
    elif platform == "wechat":
        return [f"{base}", "职场干货", "工具教程"]
    else:  # zhihu
        return [topic, "职场", "成长", "干货", "经验分享"]


# ─────────────────────────────────────────────
# Hot Topic Generator
# ─────────────────────────────────────────────

def generate_hot_topics(niche: str, count: int = 5) -> List[Dict]:
    """Generate trending topic suggestions."""
    now = datetime.now()
    weekday = now.weekday()
    topics = []

    base_topics = [
        f"{niche}高效工作法",
        f"AI时代{niche}新思路",
        f"{niche}常见误区盘点",
        f"从0到1搞定{niche}",
        f"{niche}进阶指南",
    ]

    type_labels = ["结果导向型", "痛点共鸣型", "认知反差型", "教程干货型", "揭秘型"]
    for i, t in enumerate(base_topics[:count]):
        topics.append({
            "id": i + 1,
            "title": t,
            "type": type_labels[i % len(type_labels)],
            "pain_point": f"打工人最困扰的「{niche}」问题",
            "tags": _generate_tags(t, platform="xiaohongshu")[:5],
            "angle": "真实分享+可复制方法",
        })
    return topics


def search_trending_topics(keyword: str, platform: str = "all") -> List[Dict]:
    """
    搜索实时热门话题（通过搜索引擎）
    keyword: 关键词
    platform: xiaohongshu/zhihu/douyin/all
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        results = []
        
        # 搜索URL
        search_urls = {
            "xiaohongshu": f"https://www.xiaohongshu.com/search_result?keyword={keyword}",
            "zhihu": f"https://www.zhihu.com/search?type=content&q={keyword}",
            "douyin": f"https://www.douyin.com/search/{keyword}",
            "all": f"https://www.baidu.com/s?wd={keyword}+热门话题"
        }
        
        url = search_urls.get(platform, search_urls["all"])
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,*/*'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results.append({
                "keyword": keyword,
                "platform": platform,
                "url": url,
                "status": "searched",
                "note": "请访问URL查看完整热门话题"
            })
        else:
            results.append({
                "keyword": keyword,
                "platform": platform,
                "error": f"HTTP {response.status_code}"
            })
            
    except Exception as e:
        results.append({
            "keyword": keyword,
            "error": str(e),
            "fallback": "使用内置热门话题模板"
        })
    
    return results


# ─────────────────────────────────────────────
# Content Calendar Generator
# ─────────────────────────────────────────────

def generate_content_calendar(
    brand: str,
    platforms: List[str],
    weeks: int = 4,
    content_pillars: Optional[List[str]] = None,
) -> List[Dict]:
    """Generate structured content calendar."""
    if content_pillars is None:
        content_pillars = ["干货教程", "互动话题", "产品推广", "个人IP"]

    calendar = []
    mix_keys = list(CONTENT_MIX.keys())
    mix_vals = list(CONTENT_MIX.values())

    start_date = datetime.now()
    for week in range(weeks):
        for day_offset in range(7):
            date = start_date + timedelta(weeks=week, days=day_offset)
            platform = platforms[day_offset % len(platforms)]
            pillar = content_pillars[day_offset % len(content_pillars)]
            mix_type = mix_keys[int(day_offset * len(mix_keys) / 7) % len(mix_keys)]

            post = {
                "date": date.strftime("%Y-%m-%d"),
                "day": ["周一","周二","周三","周四","周五","周六","周日"][day_offset],
                "platform": platform,
                "content_type": _guess_content_type(mix_type),
                "content_pillar": pillar,
                "mix_category": mix_type,
                "caption": f"[{mix_type.upper()}] {pillar}内容 - {date.strftime('%Y-%m-%d')}",
                "hashtags": {
                    "primary": [f"#{brand}", f"#{pillar}"],
                    "secondary": ["#"+p for p in content_pillars[:3]],
                    "niche": [f"#{brand}tips"],
                },
                "image_prompt": f"{brand} {platform} {pillar} social media image",
                "cta": "Save this post | Comment below | Share with friends",
                "notes": f"Week {week+1}, Day {day_offset+1}",
            }
            calendar.append(post)
    return calendar


def _guess_content_type(mix_category: str) -> str:
    """Map content mix category to content type."""
    mapping = {
        "educational": "tutorial",
        "engaging": "question_poll",
        "promotional": "product",
        "personal": "bts_story",
    }
    return mapping.get(mix_category, "post")


# ─────────────────────────────────────────────
# Batch Generator
# ─────────────────────────────────────────────

def batch_generate(topic: str, platform: str, count: int = 5) -> List[Dict]:
    """Batch generate content variants."""
    angles = [
        "结果导向：强调效果和收益",
        "痛点共鸣：戳中用户困扰",
        "认知反差：打破常见误区",
        "实操教程：手把手步骤",
        "个人故事：真实经历分享",
    ]
    results = []
    for i in range(min(count, len(angles))):
        angle = angles[i % len(angles)]
        if platform == "xiaohongshu":
            content = render_xiaohongshu(topic, angle)
        elif platform == "zhihu":
            content = render_zhihu(f"如何{topic}？", topic, angle)
        elif platform == "douyin":
            content = render_douyin(topic, angle)
        else:
            content = render_wechat(topic, angle)

        results.append({
            "id": i + 1,
            "title": content.get("headline", content.get("hook", ""))[:50],
            "angle": angle,
            "platform": platform,
            "tag_count": len(content.get("tags", [])),
            "scene": _describe_scene(platform, i),
            "content": content,
        })
    return results


def _describe_scene(platform: str, idx: int) -> str:
    scenes = {
        "xiaohongshu": ["通勤路上刷到", "午休时间阅读", "收藏夹常驻", "朋友圈分享", "评论区讨论"],
        "zhihu": ["搜索问题看到", "推荐页刷到", "收藏反复看", "转发给同事"],
        "douyin": ["刷到停不下来", "点赞后反复看", "转发给朋友"],
        "wechat": ["公众号推送", "朋友圈转发", "同事群分享"],
    }
    platform_scenes = scenes.get(platform, scenes["xiaohongshu"])
    return platform_scenes[idx % len(platform_scenes)]


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Creation Pro Generator")
    parser.add_argument("--mode", choices=["single", "calendar", "batch", "topics"], required=True)
    parser.add_argument("--platform", default="xiaohongshu")
    parser.add_argument("--topic", default="AI写作技巧")
    parser.add_argument("--angle", default="效率提升")
    parser.add_argument("--brand", default="MyBrand")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--weeks", type=int, default=4)
    parser.add_argument("--output", default="./output")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.mode == "single":
        if args.platform == "xiaohongshu":
            out = render_xiaohongshu(args.topic, args.angle)
        elif args.platform == "zhihu":
            out = render_zhihu(args.topic, args.topic, args.angle)
        elif args.platform == "douyin":
            out = render_douyin(args.topic, args.angle)
        else:
            out = render_wechat(args.topic, args.angle)
        print(json.dumps(out, ensure_ascii=False, indent=2))

    elif args.mode == "topics":
        topics = generate_hot_topics(args.topic, count=args.count)
        print(json.dumps(topics, ensure_ascii=False, indent=2))

    elif args.mode == "calendar":
        cal = generate_content_calendar(args.brand, args.platform.split(","), weeks=args.weeks)
        fn = os.path.join(args.output, f"calendar_{ts}.json")
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)
        print(f"Calendar saved: {fn} ({len(cal)} posts)")

    elif args.mode == "batch":
        results = batch_generate(args.topic, args.platform, count=args.count)
        fn = os.path.join(args.output, f"batch_{args.platform}_{ts}.json")
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Batch content saved: {fn} ({len(results)} variants)")
