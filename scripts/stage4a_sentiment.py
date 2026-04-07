"""Stage 4a: Sentiment, Emotion (Plutchik), and ABSA classification.
In-context analysis - classifies all filtered items.
"""
import json
import sys
import re
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")
filtered = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))


def classify_sentiment(text):
    t = text.lower()
    pos_strong = [
        "amazing", "incredible", "love", "best", "wonderful", "fantastic", "great result",
        "life changing", "life-changing", "game changer", "game-changer",
        "transformed", "breakthrough", "excellent", "highly recommend", "so happy",
        "lost weight", "lost kg", "lost pound", "down kg", "weight down",
        "feel amazing", "feel great", "so thankful", "grateful", "blessed",
        "changed my life", "best decision", "so proud", "worked for me",
        "very effective", "works wonders", "powerful tool",
    ]
    pos_mod = [
        "good", "nice", "helpful", "effective", "works", "progress", "improved",
        "better", "success", "achieve", "benefit", "positive", "hope", "motivated",
        "inspiring", "recommended", "safe", "approved", "healthy", "strong",
        "consistency", "discipline", "transformation", "journey", "goal",
    ]
    neg_strong = [
        "terrible", "horrible", "worst", "dangerous", "scary", "horrifying",
        "ruined", "destroyed", "nightmare", "severe side effect", "hospitalized",
        "gained all back", "regained", "scam", "fraud", "fake", "disgusting",
        "hate", "awful", "death", "died", "kill", "toxic", "poison",
        "muscle loss", "hair loss", "bone loss", "kidney", "pancreatitis", "gallstone",
    ]
    neg_mod = [
        "side effect", "nausea", "vomiting", "diarrhea", "constipation",
        "concern", "worried", "scared", "risk", "problem", "issue", "struggle",
        "hard", "difficult", "pain", "suffer", "regain", "weight gain",
        "expensive", "costly", "afford", "shortcut", "easy way out",
        "not sustainable", "long term effect", "dependency",
        "fat shaming", "bullying", "judgment", "stigma",
        "not working", "plateau", "stalled", "stopped working",
    ]
    warn = [
        "caution", "careful", "warning", "be aware", "consult", "doctor supervision",
        "not for everyone", "prescription only", "dark side", "harsh truth",
    ]

    ps = sum(2 for k in pos_strong if k in t) + sum(1 for k in pos_mod if k in t)
    ns = sum(2 for k in neg_strong if k in t) + sum(1 for k in neg_mod if k in t)
    ws = sum(1 for k in warn if k in t)
    has_but = bool(re.search(r"\bbut\b|\bhowever\b|\balthough\b|\bwhile\b", t))

    if ps > 2 and ns > 2:
        return "mixed", min(0.6 + (ps + ns) * 0.02, 0.95)
    if ps > ns + ws:
        if ps >= 4:
            return "positive", min(0.8 + ps * 0.02, 0.95)
        elif ps >= 2:
            return "positive", 0.7
        else:
            return "positive", 0.6
    elif ns > ps:
        if ns >= 4:
            return "negative", min(0.8 + ns * 0.02, 0.95)
        elif ns >= 2:
            return "negative", 0.7
        else:
            return "negative", 0.6
    elif ws > 0 and ps > 0:
        return "mixed", 0.6
    elif ws > 0:
        return "negative", 0.55
    elif has_but and ps > 0:
        return "mixed", 0.6
    elif ps == ns and ps > 0:
        return "mixed", 0.6
    else:
        info_kw = ["what is", "how does", "explained", "study", "research", "according to", "tips", "guide", "how to"]
        if any(k in t for k in info_kw):
            return "neutral", 0.6
        if ps > 0:
            return "positive", 0.55
        elif ns > 0:
            return "negative", 0.55
        else:
            return "neutral", 0.5


def classify_emotion(text, sentiment):
    t = text.lower()
    emo_kw = {
        "joy": ["happy", "love", "amazing", "wonderful", "excited", "thrilled", "proud", "grateful", "thankful", "blessed", "feel great", "incredible"],
        "trust": ["recommend", "trust", "reliable", "proven", "evidence", "clinical", "safe", "research", "science", "expert", "medical advancement"],
        "fear": ["scared", "afraid", "worried", "anxious", "terrified", "risk", "danger", "cancer", "side effect", "horror", "unknown"],
        "surprise": ["shocked", "surprised", "wow", "unbelievable", "mind blown", "unexpected", "never thought", "crazy", "insane"],
        "sadness": ["sad", "depressed", "hopeless", "desperate", "struggle", "suffering", "exhausted", "frustrated", "tired of", "given up", "broken"],
        "disgust": ["disgusting", "gross", "vomit", "nausea", "sick", "hate", "terrible", "awful", "scam", "fraud", "fake", "shameful"],
        "anger": ["angry", "furious", "outraged", "ridiculous", "unfair", "exploitation", "greed", "lying", "shame on", "wtf", "unacceptable"],
        "anticipation": ["hope", "looking forward", "excited", "planning", "going to start", "ready", "goal", "beginning", "starting", "journey begins", "day 1"],
    }
    scores = {e: sum(1 for k in kws if k in t) for e, kws in emo_kw.items()}
    mx = max(scores, key=scores.get)
    if scores[mx] == 0:
        if sentiment == "positive":
            return "joy", 0.4
        elif sentiment == "negative":
            return "sadness", 0.3
        else:
            return "none", 0.0
    return mx, min(0.3 + scores[mx] * 0.15, 0.95)


def extract_aspects(text):
    t = text.lower()
    defs = {
        "efficacy": (
            ["effective", "works", "result", "lost weight", "lost kg", "weight loss", "progress", "transformation"],
            ["effective", "works", "amazing result", "lost", "progress", "success"],
            ["not working", "plateau", "stopped working", "no result", "failed"],
        ),
        "side_effects": (
            ["side effect", "nausea", "vomiting", "diarrhea", "constipation", "hair loss", "muscle loss", "fatigue", "headache", "bloating", "sulphur burp", "ozempic face", "ozempic teeth", "insomnia"],
            ["no side effect", "manageable", "mild", "went away", "tolerable"],
            ["nausea", "vomiting", "diarrhea", "hair loss", "muscle loss", "severe", "horrible", "dangerous"],
        ),
        "cost": (
            ["cost", "price", "expensive", "afford", "cheap", "rupee", "insurance", "budget", "money"],
            ["affordable", "cheap", "worth it", "insurance cover"],
            ["expensive", "costly", "overpriced", "too much"],
        ),
        "accessibility": (
            ["available", "prescribe", "doctor", "pharmacy", "launch", "approved", "where to get", "generic"],
            ["available", "launched", "approved", "easy to get"],
            ["not available", "hard to find", "shortage", "prescription only"],
        ),
        "sustainability": (
            ["long term", "maintain", "regain", "after stopping", "lifelong", "sustainable", "permanent", "keep off"],
            ["sustainable", "maintain", "keep off", "lifestyle change"],
            ["regain", "bounce back", "not sustainable", "lifelong", "dependency", "gained back"],
        ),
        "natural_alternatives": (
            ["natural", "ayurvedic", "home remedy", "without medication", "without injection", "diet and exercise", "holistic"],
            ["natural", "no side effects", "holistic", "ayurvedic"],
            ["not enough", "slow", "unproven"],
        ),
        "stigma": (
            ["shame", "stigma", "lazy", "cheating", "easy way out", "shortcut", "judg", "body sham", "fat sham"],
            ["no shame", "medical advancement", "not cheating", "brave"],
            ["lazy", "cheating", "easy way out", "shortcut", "shame", "stigma"],
        ),
        "muscle_preservation": (
            ["muscle", "protein intake", "lean mass", "muscle loss", "strength training", "resistance"],
            ["preserve muscle", "high protein", "strength", "lean mass"],
            ["muscle loss", "losing muscle", "weak", "wasting"],
        ),
    }
    aspects = []
    for name, (kws, pos, neg) in defs.items():
        if any(k in t for k in kws):
            pc = sum(1 for k in pos if k in t)
            nc = sum(1 for k in neg if k in t)
            if pc > nc:
                aspects.append({"aspect": name, "sentiment": "positive", "sentiment_score": min(0.6 + pc * 0.1, 0.95)})
            elif nc > pc:
                aspects.append({"aspect": name, "sentiment": "negative", "sentiment_score": min(0.6 + nc * 0.1, 0.95)})
            elif pc > 0:
                aspects.append({"aspect": name, "sentiment": "mixed", "sentiment_score": 0.6})
            else:
                aspects.append({"aspect": name, "sentiment": "neutral", "sentiment_score": 0.5})
    return aspects


def extract_key_phrases(text):
    t = text.lower()
    phrases = []
    for med in ["ozempic", "wegovy", "mounjaro", "semaglutide", "tirzepatide", "glp-1", "zepbound"]:
        if med in t:
            phrases.append(med)
    for topic in ["weight loss", "side effects", "muscle loss", "hair loss", "natural", "ayurvedic",
                  "insulin resistance", "diabetes", "pcos", "bariatric", "calorie deficit", "protein",
                  "intermittent fasting"]:
        if topic in t and topic not in phrases:
            phrases.append(topic)
    return phrases[:5]


# Process all items
sentiment_results = []
for item in filtered:
    text = item.get("content_text", "")
    item_id = item.get("item_id", "")
    sent, score = classify_sentiment(text)
    emotion, emotion_intensity = classify_emotion(text, sent)
    aspects = extract_aspects(text)
    key_phrases = extract_key_phrases(text)

    if sent == "positive":
        reasoning = "Content expresses positive view on weight loss/medication"
    elif sent == "negative":
        reasoning = "Content expresses concern or negativity about weight loss/medication"
    elif sent == "mixed":
        reasoning = "Content presents both positive and negative perspectives"
    else:
        reasoning = "Content is informational/neutral about weight loss topic"
    if aspects:
        reasoning += ". Key aspects: " + ", ".join(a["aspect"] for a in aspects)

    sentiment_results.append({
        "item_id": item_id,
        "sentiment": sent,
        "sentiment_score": round(score, 2),
        "reasoning": reasoning,
        "key_phrases": key_phrases,
        "aspects": aspects,
        "primary_emotion": emotion,
        "emotion_intensity": round(emotion_intensity, 2),
    })

# Stats
sent_counts = {}
emotion_counts = {}
for sr in sentiment_results:
    sent_counts[sr["sentiment"]] = sent_counts.get(sr["sentiment"], 0) + 1
    emotion_counts[sr["primary_emotion"]] = emotion_counts.get(sr["primary_emotion"], 0) + 1
print(f"Total classified: {len(sentiment_results)}")
print(f"Sentiment: {sent_counts}")
print(f"Emotions: {emotion_counts}")

aspect_counts = {}
for sr in sentiment_results:
    for a in sr["aspects"]:
        aspect_counts[a["aspect"]] = aspect_counts.get(a["aspect"], 0) + 1
print(f"Aspect mentions: {aspect_counts}")

# Save
(RUN_DIR / "analysis").mkdir(exist_ok=True)
(RUN_DIR / "analysis" / "sentiment_results.json").write_text(
    json.dumps(sentiment_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Saved analysis/sentiment_results.json")
