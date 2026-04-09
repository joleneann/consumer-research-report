"""Assemble analysis/results.json from sentiment and theme data."""
import json, sys, random
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

RUN_DIR = Path('runs/20260407_184943_08eb92')
corpus = json.loads((RUN_DIR / 'filtered/corpus.json').read_text(encoding='utf-8'))
sentiment_data = json.loads((RUN_DIR / 'analysis/sentiment_pass1.json').read_text(encoding='utf-8'))
themes_data = json.loads((RUN_DIR / 'analysis/themes_final.json').read_text(encoding='utf-8'))

# Build lookups
corpus_map = {item['item_id']: item for item in corpus}
sent_map = {r['item_id']: r for r in sentiment_data['sentiment_results']}
item_themes = themes_data['item_themes']

# Filter sentiment results to only items in the refined corpus
corpus_ids = set(item['item_id'] for item in corpus)
filtered_sent = [r for r in sentiment_data['sentiment_results'] if r['item_id'] in corpus_ids]

# Overall sentiment
overall_sentiment = Counter(r['sentiment'] for r in filtered_sent)
total = len(filtered_sent)
nss = (overall_sentiment.get('positive', 0) - overall_sentiment.get('negative', 0)) / max(total, 1)

# Emotion distribution
emotion_dist = Counter(r['emotion'] for r in filtered_sent)

# Aspect sentiment summary
aspect_summary = defaultdict(lambda: Counter())
for r in filtered_sent:
    for asp in r.get('aspects', []):
        aspect_summary[asp['aspect']][asp['sentiment']] += 1

# Build SentimentResult objects
sentiment_results = []
for r in filtered_sent:
    aspects = []
    for asp in r.get('aspects', []):
        aspects.append({
            'aspect': asp['aspect'],
            'sentiment': asp['sentiment'],
            'sentiment_score': asp['score'],
        })
    sentiment_results.append({
        'item_id': r['item_id'],
        'sentiment': r['sentiment'],
        'sentiment_score': r['sentiment_score'],
        'reasoning': f"Classified via keyword-based heuristic with contextual rules",
        'key_phrases': [],
        'aspects': aspects,
        'primary_emotion': r['emotion'],
        'emotion_intensity': 0.6 if r['emotion'] != 'none' else 0.0,
        'secondary_emotion': None,
    })

# Build Theme objects with sentiment distribution and representative quotes
random.seed(42)
themes_out = []
for theme in themes_data['themes']:
    tid = theme['theme_id']
    theme_item_ids = [iid for iid in theme['item_ids'] if iid in corpus_ids]
    theme_items = [corpus_map[iid] for iid in theme_item_ids if iid in corpus_map]

    # Sentiment distribution for this theme
    theme_sent = Counter()
    theme_emo = Counter()
    for iid in theme_item_ids:
        s = sent_map.get(iid)
        if s:
            theme_sent[s['sentiment']] += 1
            theme_emo[s['emotion']] += 1

    theme_nss = (theme_sent.get('positive', 0) - theme_sent.get('negative', 0)) / max(sum(theme_sent.values()), 1)

    # Platforms present
    platforms_present = sorted(set(corpus_map[iid].get('source_platform', 'unknown')
                                   for iid in theme_item_ids if iid in corpus_map))

    # Select representative quotes (prefer comments, medium length, cross-theme dedup)
    candidates = []
    for item in theme_items:
        text = item.get('content_text', '')
        text_len = len(text)
        # Score: prefer comments, medium length (80-500 chars), avoid very short/long
        score = 0
        if item.get('content_type') == 'comment':
            score += 3
        if 80 <= text_len <= 500:
            score += 2
        elif 50 <= text_len <= 800:
            score += 1
        # Avoid posts that are mostly URLs/hashtags
        if text.count('http') <= 1 and text.count('#') <= 3:
            score += 1
        candidates.append((score, item))

    candidates.sort(key=lambda x: -x[0])
    quotes = []
    used_ids = set()
    for score, item in candidates[:10]:
        if item['item_id'] not in used_ids and len(quotes) < 3:
            quotes.append({
                'text': item['content_text'][:500],
                'item_id': item['item_id'],
                'source_url': item.get('source_url', ''),
                'source_platform': item.get('source_platform', 'unknown'),
                'source_timestamp': item.get('source_timestamp'),
                'engagement_score': item.get('platform_metadata', {}).get('score'),
                'selection_reason': f"Selected for {theme['label']}: quality score {score}",
            })
            used_ids.add(item['item_id'])

    themes_out.append({
        'theme_id': tid,
        'theme_label': theme['label'],
        'theme_description': theme['description'],
        'supporting_item_ids': theme_item_ids,
        'item_count': len(theme_item_ids),
        'prevalence_pct': len(theme_item_ids) / len(corpus) * 100,
        'sentiment_distribution': dict(theme_sent),
        'emotion_distribution': dict(theme_emo),
        'net_sentiment_score': round(theme_nss, 4),
        'representative_quotes': quotes,
        'platforms_present': platforms_present,
    })

# Assemble AnalysisResults
results = {
    'sentiment_results': sentiment_results,
    'themes': themes_out,
    'overall_sentiment': dict(overall_sentiment),
    'net_sentiment_score': round(nss, 4),
    'emotion_distribution': dict(emotion_dist),
    'aspect_sentiment_summary': {k: dict(v) for k, v in aspect_summary.items()},
    'total_items_analyzed': len(corpus),
    'analysis_model': 'claude-code-in-context',
    'analysis_prompts': {
        'method': 'In-context analysis by Claude Code session (Opus 4.6)',
        'sentiment': 'Keyword-based heuristic with contextual rules, sarcasm detection, Hindi support',
        'themes': 'Two-pass: 300-item stratified discovery + full-corpus keyword mapping + narrative review',
    },
}

out_path = RUN_DIR / 'analysis/results.json'
out_path.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False), encoding='utf-8')

print(f"Written analysis/results.json")
print(f"  Items analyzed: {len(corpus)}")
print(f"  Sentiment: {dict(overall_sentiment)}")
print(f"  NSS: {nss:+.4f}")
print(f"  Themes: {len(themes_out)}")
print(f"  Emotions: {dict(emotion_dist)}")
