"""Assemble analysis results from sentiment + theme mapping into AnalysisResults."""
import json
import sys
import random
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

run_dir = Path('runs/20260407_143544_98a8c6')
corpus = json.loads((run_dir / 'filtered' / 'corpus.json').read_text(encoding='utf-8'))
sentiment_data = json.loads((run_dir / 'filtered' / 'sentiment_results.json').read_text(encoding='utf-8'))
theme_mapping = json.loads((run_dir / 'analysis' / 'theme_mapping.json').read_text(encoding='utf-8'))

# Build lookup
corpus_by_id = {item['item_id']: item for item in corpus}
sentiment_by_id = {s['item_id']: s for s in sentiment_data}

# Overall sentiment
overall_sentiment = Counter()
emotion_distribution = Counter()
for s in sentiment_data:
    overall_sentiment[s['sentiment']] += 1
    emotion_distribution[s['primary_emotion']] += 1

nss = round((overall_sentiment['positive'] - overall_sentiment['negative']) / len(sentiment_data), 4) if sentiment_data else 0.0

# Aspect sentiment summary
aspect_summary = defaultdict(lambda: Counter())
for s in sentiment_data:
    for asp in s.get('aspects', []):
        aspect_summary[asp['aspect']][asp['sentiment']] += 1

# Build SentimentResult objects
sentiment_results = []
for s in sentiment_data:
    aspects = []
    for asp in s.get('aspects', []):
        aspects.append({
            'aspect': asp['aspect'],
            'sentiment': asp['sentiment'],
            'sentiment_score': asp['score'],
        })
    sentiment_results.append({
        'item_id': s['item_id'],
        'sentiment': s['sentiment'],
        'sentiment_score': s['sentiment_score'],
        'reasoning': 'Classified by keyword heuristics with star-rating signals',
        'key_phrases': [],
        'aspects': aspects,
        'primary_emotion': s['primary_emotion'],
        'emotion_intensity': 0.5 if s['primary_emotion'] != 'none' else 0.0,
        'secondary_emotion': None,
    })

# Build Theme objects
random.seed(42)
themes_data = theme_mapping['themes']
item_themes_map = theme_mapping['item_themes']

theme_objects = []
for theme_id in sorted(themes_data.keys()):
    tdata = themes_data[theme_id]
    item_ids = tdata['item_ids']

    # Sentiment distribution for this theme
    theme_sentiment = Counter()
    theme_emotion = Counter()
    theme_platforms = set()

    for iid in item_ids:
        s = sentiment_by_id.get(iid)
        if s:
            theme_sentiment[s['sentiment']] += 1
            theme_emotion[s['primary_emotion']] += 1
        item = corpus_by_id.get(iid)
        if item:
            theme_platforms.add(item['source_platform'])

    # NSS for theme
    total = sum(theme_sentiment.values())
    theme_nss = round((theme_sentiment['positive'] - theme_sentiment['negative']) / total, 4) if total > 0 else 0.0

    # Select representative quotes (prefer comments/reviews with moderate length)
    candidate_items = []
    for iid in item_ids:
        item = corpus_by_id.get(iid)
        if item:
            text = item['content_text']
            # Prefer reviews and comments, moderate length
            score = 0
            if item['content_type'] == 'review':
                score += 3
            elif item['content_type'] == 'comment':
                score += 2
            if 80 <= len(text) <= 500:
                score += 3
            elif 50 <= len(text) <= 800:
                score += 1
            candidate_items.append((iid, item, score))

    candidate_items.sort(key=lambda x: x[2], reverse=True)
    quotes = []
    for iid, item, score in candidate_items[:3]:
        quotes.append({
            'text': item['content_text'][:500],
            'item_id': iid,
            'source_url': item.get('source_url', ''),
            'source_platform': item['source_platform'],
            'source_timestamp': item.get('source_timestamp'),
            'engagement_score': item.get('platform_metadata', {}).get('score'),
            'selection_reason': f'Top-scoring quote for theme (score={score})',
        })

    platforms_list = sorted(theme_platforms)

    theme_objects.append({
        'theme_id': theme_id,
        'theme_label': tdata['label'],
        'theme_description': tdata['description'],
        'supporting_item_ids': item_ids,
        'item_count': len(item_ids),
        'prevalence_pct': round(len(item_ids) / len(corpus) * 100, 2),
        'sentiment_distribution': dict(theme_sentiment),
        'emotion_distribution': dict(theme_emotion),
        'net_sentiment_score': theme_nss,
        'representative_quotes': quotes,
        'platforms_present': platforms_list,
        'is_multi_source': len(theme_platforms) >= 2,
        'is_contested': False,
    })

# Assemble AnalysisResults
analysis = {
    'sentiment_results': sentiment_results,
    'themes': theme_objects,
    'overall_sentiment': dict(overall_sentiment),
    'net_sentiment_score': nss,
    'emotion_distribution': dict(emotion_distribution),
    'aspect_sentiment_summary': {k: dict(v) for k, v in aspect_summary.items()},
    'total_items_analyzed': len(corpus),
    'analysis_model': 'claude-code-in-context',
    'analysis_prompts': {'method': 'In-context analysis by Claude Code session with keyword-based heuristics'},
}

(run_dir / 'analysis' / 'results.json').write_text(
    json.dumps(analysis, indent=2, default=str), encoding='utf-8'
)

print(f'Analysis results written:')
print(f'  Sentiment results: {len(sentiment_results)}')
print(f'  Themes: {len(theme_objects)}')
print(f'  Overall sentiment: {dict(overall_sentiment)}')
print(f'  NSS: {nss}')
print(f'  Emotion distribution: {dict(emotion_distribution)}')
print(f'  Aspects: {list(aspect_summary.keys())}')
