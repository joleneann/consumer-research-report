"""Sentiment, emotion, and ABSA classifier for in-context analysis."""
import json, re, sys, random
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

RUN_DIR = Path('runs/20260407_184943_08eb92')
corpus = json.loads((RUN_DIR / 'filtered/corpus.json').read_text(encoding='utf-8'))


def classify_sentiment(text):
    text_lower = text.lower()

    strong_pos = [
        'success', 'successful', 'succeeded', 'succeeds',
        'boom', 'booming', 'growth', 'growing',
        'milestone', 'boost', 'boosted', 'boosting',
        'achievement', 'achieved', 'accomplishment',
        'proud', 'pride', 'proudly',
        'great', 'amazing', 'impressive', 'incredible', 'remarkable',
        'progress', 'progressive', 'progressing',
        'surge', 'surging', 'soaring', 'soar',
        'record high', 'record breaking',
        'revolution', 'revolutionised', 'revolutionary', 'revolutionized',
        'transform', 'transformed', 'transforming', 'transformation',
        'opportunity', 'opportunities',
        'winning', 'winner',
        'leading', 'leader', 'leadership',
        'excellent', 'outstanding', 'phenomenal',
        'thriving', 'flourishing', 'prospering',
        'game changer', 'game-changer', 'world class', 'world-class',
        'bright future', 'promising', 'optimistic',
        'champion', 'pioneering',
        'historic', 'breakthrough', 'innovation', 'innovative',
        'commendable', 'laudable', 'praiseworthy',
        'well done', 'kudos', 'bravo', 'hats off',
        'good news', 'encouraging',
        'empowering', 'strengthening', 'rising',
        'leap', 'leapfrog',
        'massive investment', 'huge investment',
        'job creation', 'jobs created', 'employment generation',
        'export growth', 'export surge', 'export boom',
        'manufacturing hub', 'global hub',
        'self reliant', 'self-reliant', 'self reliance',
        'atmanirbhar', 'aatmanirbhar',
        'india rising', 'rising india', 'new india',
        'superpower', 'vishwaguru',
        'proud moment', 'proud indian',
        'bold leadership', 'visionary', 'vision',
        'credit', 'deserves credit',
        'resilience', 'resilient',
        'world leader', 'global leader',
        'well planned', 'well executed',
    ]

    strong_neg = [
        'fail', 'failed', 'failure', 'failing', 'fails',
        'scam', 'fraud', 'fraudulent',
        'worst', 'terrible', 'horrible', 'awful', 'dreadful',
        'disaster', 'disastrous', 'catastrophe',
        'joke', 'laughing stock', 'laughingstock', 'clown',
        'corrupt', 'corruption',
        'crisis', 'crises',
        'poor quality', 'inferior', 'substandard', 'low quality',
        'behind', 'backward', 'backwards', 'lagging',
        'ruin', 'ruined', 'ruining', 'destroy', 'destroyed',
        'collapse', 'collapsed', 'collapsing',
        'sham', 'hollow', 'empty promises',
        'flop', 'flopped', 'bust',
        'pathetic', 'shameful', 'shameless', 'disgraceful',
        'mess', 'messy', 'chaotic', 'chaos',
        'broken', 'dysfunctional',
        'stagnant', 'stagnation', 'declining', 'decline',
        'deteriorating', 'deterioration', 'worsening',
        'exploitation', 'exploiting', 'exploited',
        'propaganda', 'misleading', 'deceptive',
        'looting', 'loot', 'plunder',
        'suffering', 'misery', 'miserable',
        'unemployment', 'unemployed', 'jobless', 'joblessness',
        'poverty', 'struggle', 'struggling',
        'incompetent', 'incompetence',
        'slave', 'slavery', 'cheap labor', 'cheap labour',
        'no innovation', 'no quality', 'no infrastructure',
        'dumping ground', 'inferior products',
        'trade deficit',
        'brain drain', 'talent leaving',
        'just a slogan', 'empty slogan', 'only slogan',
        'worried', 'alarming',
        'dangerous', 'threat', 'threatening',
        'nothing has changed', 'no change', 'same old',
        'lip service', 'tokenism',
        'overhype', 'overhyped', 'overrated',
        'disappointed', 'disappointing', 'disappointment',
        'losing', 'loss',
        'weak', 'weakness', 'weaker',
        'anti national', 'anti-national',
        'screw driver', 'screwdriver technology',
        'snail speed', 'obsolete',
        'uneconomical', 'uncompetitive',
    ]

    sarcasm_markers = [
        r'truly a land', r'the success\s*-', r'so-called',
        r'by rosting', r'laughingstock', r'what clown',
        r'grand success indeed', r'is just a slogan',
        r'".*success.*"', r'"FAILED"',
        r'success\s*hai\s*toh',
    ]

    pos_score = sum(1 for w in strong_pos if w in text_lower)
    neg_score = sum(1 for w in strong_neg if w in text_lower)

    is_sarcastic = any(re.search(m, text_lower) for m in sarcasm_markers)
    if is_sarcastic and pos_score > 0:
        neg_score += pos_score
        pos_score = 0

    if re.search(r'not\s+a?\s*fail', text_lower):
        neg_score = max(0, neg_score - 1)
        pos_score += 1
    if re.search(r'not\s+a?\s*success', text_lower):
        pos_score = max(0, pos_score - 1)
        neg_score += 1

    if pos_score > 0 and neg_score > 0:
        if pos_score > neg_score * 2:
            return 'positive', min(0.7, 0.5 + pos_score * 0.05)
        elif neg_score > pos_score * 2:
            return 'negative', min(0.7, 0.5 + neg_score * 0.05)
        return 'mixed', 0.5
    elif pos_score > 0:
        return 'positive', min(0.9, 0.5 + pos_score * 0.1)
    elif neg_score > 0:
        return 'negative', min(0.9, 0.5 + neg_score * 0.1)

    if '?' in text and re.search(r'(why|how come|where|what happened|really\??$)', text_lower):
        return 'negative', 0.4

    # Pro-India / support local / vocal for local
    if re.search(r'(support\w* indian|buy indian|proud to be|jai hind|vande mataram|bharat mata ki jai|choose swadeshi|go for made in india|ditch import|go local|made in india.*better|indian.*better than|choose indian|prefer indian|switch to indian|vocal for local|go desi|shop indian|love.*indian brand|indian brand.*love|support local|back indian|choose desi)', text_lower):
        return 'positive', 0.6

    # Hindi positive sentiment
    if re.search(r'(badhai|shandaar|shubh|garv|gaurav|samridh|vikas|aatmanirbhar|swadeshi apnao|desh.*taraqqi|pragati|safalta)', text_lower):
        return 'positive', 0.6

    # Criticism without explicit failure words
    if re.search(r'(wake up|open your eyes|reality check|ground reality|on paper|not in reality|just on paper|3rd rate|third rate|cheap.*product|can.t compete|cannot compete|no.one.*care|system.*not.*work|what.*joke|waste.*money|waste.*time|full of shit|dumbass|idiot|foolish|stupid|bullshit|nonsense|crap|joke of|laughable|shame on|blaming|lying|liars|sold.*india|sell.*india|selling.*india|assembly.*not.*manufactur|assembl.*unit|not.*manufactur|chinese spy|anti.national|won.t invest|never invest|typical indian|too emotional|refuse.*change)', text_lower):
        return 'negative', 0.5

    # Hindi negative sentiment
    if re.search(r'(nakli|ghatiya|bekar|barbaad|barbadi|asafalta|dhoka|fraud|paap|gaddar|nikamma|tukde|andh bhakt|andhbhakt|bikau|bikau|nautanki)', text_lower):
        return 'negative', 0.5

    # Mixed / balanced take
    if re.search(r'(on one hand|two sides|both.*success.*fail|both.*fail.*success|pros.*cons|cons.*pros|mixed.*result|debatable|nuanced|complex.*(issue|topic)|some.*good.*some.*bad)', text_lower):
        return 'mixed', 0.5

    # Implicit positive: sharing achievements, data showing growth
    if re.search(r'(\d+.*jobs.*created|\d+.*billion.*invest|\d+.*crore.*invest|\d+%.*growth|exports.*grew|exports.*increased|production.*increased|manufacturing.*increased|up\s+\d+%|grew\s+\d+%|jumped\s+\d+%|rose\s+\d+%)', text_lower):
        return 'positive', 0.55

    # Implicit negative: sharing problems, data showing decline
    if re.search(r'(deficit.*\d+|debt.*\d+|declined\s+\d+%|fell\s+\d+%|dropped\s+\d+%|shrunk|shrank|decreased)', text_lower):
        return 'negative', 0.45

    return 'neutral', 0.5


def classify_emotion(text, sentiment):
    text_lower = text.lower()

    joy_words = ['proud', 'pride', 'celebrate', 'amazing', 'wonderful', 'fantastic', 'brilliant', 'thrilled', 'excited', 'happy', 'delighted', 'kudos', 'bravo', 'love it', 'awesome']
    trust_words = ['reliable', 'proven', 'delivered', 'confidence', 'stable', 'consistent', 'trusted', 'credible', 'fact', 'evidence', 'data shows', 'backed by', 'truth']
    anger_words = ['angry', 'outrage', 'furious', 'disgraceful', 'shameful', 'unacceptable', 'exploitation', 'looting', 'scam', 'fraud', 'corrupt', 'cheating', 'betrayal', 'liars']
    fear_words = ['crisis', 'danger', 'risk', 'collapse', 'threat', 'worried', 'alarming', 'scary', 'devastating', 'doomed']
    sadness_words = ['disappointing', 'unfortunate', 'sad', 'tragic', 'heartbreaking', 'regret', 'suffer', 'decline', 'loss', 'painful']
    disgust_words = ['disgusting', 'pathetic', 'shameless', 'joke', 'laughable', 'absurd', 'ridiculous', 'nauseating', 'sickening', 'clown']
    anticipation_words = ['potential', 'future', 'upcoming', 'expected', 'promising', 'will be', 'going to', 'hope', 'aspire', 'dream', 'vision', 'plan', 'target']
    surprise_words = ['unexpected', 'shocking', 'surprising', 'unprecedented', 'unbelievable', 'incredible', 'never thought', 'who knew', 'stunning']

    scores = {
        'joy': sum(1 for w in joy_words if w in text_lower),
        'trust': sum(1 for w in trust_words if w in text_lower),
        'anger': sum(1 for w in anger_words if w in text_lower),
        'fear': sum(1 for w in fear_words if w in text_lower),
        'sadness': sum(1 for w in sadness_words if w in text_lower),
        'disgust': sum(1 for w in disgust_words if w in text_lower),
        'anticipation': sum(1 for w in anticipation_words if w in text_lower),
        'surprise': sum(1 for w in surprise_words if w in text_lower),
    }

    # Boost based on sentiment
    if sentiment == 'positive':
        scores['joy'] += 1
        scores['trust'] += 1
        scores['anticipation'] += 1
    elif sentiment == 'negative':
        scores['anger'] += 1
        scores['sadness'] += 1

    max_emotion = max(scores, key=scores.get)
    if scores[max_emotion] == 0:
        return 'none'
    return max_emotion


def extract_aspects(text):
    text_lower = text.lower()
    aspects = []

    aspect_keywords = {
        'manufacturing': ['manufactur', 'production', 'factory', 'factories', 'assembly', 'assembl', 'industrial'],
        'job_creation': ['jobs', 'employment', 'hiring', 'workforce', 'workers', 'labour', 'labor', 'recruitment', 'unemployment', 'jobless'],
        'product_quality': ['quality', 'inferior', 'superior', 'standard', 'substandard', 'world class', 'cheap', 'durability', 'reliable'],
        'foreign_investment': ['FDI', 'foreign direct invest', 'foreign invest', 'investment', 'investor', 'capital inflow'],
        'policy_effectiveness': ['PLI', 'scheme', 'policy', 'reform', 'GST', 'incentive', 'subsidy', 'regulation', 'ease of doing'],
        'infrastructure': ['infrastructure', 'road', 'highway', 'expressway', 'airport', 'port', 'rail', 'bullet train', 'metro', 'logistics'],
        'global_competitiveness': ['china', 'compete', 'competitive', 'global market', 'world market', 'export', 'import', 'trade', 'tariff'],
        'defence': ['defence', 'defense', 'military', 'missile', 'drdo', 'brahmos', 'tejas', 'hal', 'weapon', 'ammunition'],
        'electronics_semiconductor': ['semiconductor', 'chip', 'electronics', 'mobile', 'smartphone', 'iphone', 'foxconn', 'samsung', 'apple'],
        'innovation': ['innovation', 'startup', 'technology', 'tech', 'R&D', 'research', 'patent', 'AI', 'digital'],
        'economy': ['GDP', 'economy', 'economic', 'growth rate', 'trillion', 'per capita', 'income', 'wealth'],
        'brand_perception': ['brand', 'indian brand', 'desi brand', 'swadeshi', 'local brand', 'homegrown', 'made in india'],
    }

    for aspect, keywords in aspect_keywords.items():
        if any(kw in text_lower for kw in keywords):
            # Determine aspect-level sentiment
            # Use simple heuristic: positive/negative words near aspect keywords
            aspect_context = text_lower
            pos_near = any(w in aspect_context for w in ['success', 'growth', 'boost', 'rising', 'improved', 'great', 'excellent', 'strong', 'world class'])
            neg_near = any(w in aspect_context for w in ['fail', 'poor', 'weak', 'behind', 'decline', 'crisis', 'inferior', 'no', 'lack', 'missing'])

            if pos_near and neg_near:
                asp_sent = 'mixed'
                asp_score = 0.5
            elif pos_near:
                asp_sent = 'positive'
                asp_score = 0.7
            elif neg_near:
                asp_sent = 'negative'
                asp_score = 0.3
            else:
                asp_sent = 'neutral'
                asp_score = 0.5

            aspects.append({
                'aspect': aspect,
                'sentiment': asp_sent,
                'score': asp_score
            })

    return aspects


# Process all items
sentiment_results = []
for item in corpus:
    text = item['content_text']
    sentiment, score = classify_sentiment(text)
    emotion = classify_emotion(text, sentiment)
    aspects = extract_aspects(text)

    sentiment_results.append({
        'item_id': item['item_id'],
        'sentiment': sentiment,
        'sentiment_score': score,
        'emotion': emotion,
        'aspects': aspects,
    })

# Stats
sent_counts = Counter(r['sentiment'] for r in sentiment_results)
emo_counts = Counter(r['emotion'] for r in sentiment_results)

print(f"Sentiment distribution:")
for s in ['positive', 'negative', 'neutral', 'mixed']:
    pct = sent_counts[s] / len(corpus) * 100
    print(f"  {s}: {sent_counts[s]} ({pct:.1f}%)")

print(f"\nEmotion distribution:")
for e in sorted(emo_counts.keys(), key=lambda x: -emo_counts[x]):
    pct = emo_counts[e] / len(corpus) * 100
    print(f"  {e}: {emo_counts[e]} ({pct:.1f}%)")

# Aspect frequency
asp_counts = Counter()
for r in sentiment_results:
    for a in r['aspects']:
        asp_counts[a['aspect']] += 1

print(f"\nAspect frequency:")
for a, c in asp_counts.most_common():
    print(f"  {a}: {c}")

# Save results
output = {
    'sentiment_results': sentiment_results,
    'overall_sentiment': dict(sent_counts),
    'total_classified': len(sentiment_results),
}

out_path = RUN_DIR / 'analysis'
out_path.mkdir(exist_ok=True)
(out_path / 'sentiment_pass1.json').write_text(
    json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8'
)
print(f"\nSaved to {out_path / 'sentiment_pass1.json'}")
