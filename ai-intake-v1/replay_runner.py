import json
import sys
from pathlib import Path
from collections import Counter
import httpx

BASE_URL = 'http://127.0.0.1:8000'
CORPUS_PATH = Path(__file__).with_name('synthetic_replay_corpus_100.jsonl')


def post_case(client, case):
    conversation_id = None
    for turn in case['transcript_qna']:
        payload = {
            'conversation_id': conversation_id,
            'prospect': case['prospect'],
            'role': turn['role'],
            'content': turn['content'],
        }
        res = client.post(f'{BASE_URL}/api/intake/messages', json=payload, timeout=30.0)
        res.raise_for_status()
        conversation_id = res.json()['conversation_id']
    fin = client.post(f'{BASE_URL}/api/intake/conversations/{conversation_id}/finalize', timeout=60.0)
    fin.raise_for_status()
    return conversation_id, fin.json()['summary']


def norm_secondary(items):
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(item.get('area'))
        else:
            out.append(item)
    return sorted(x for x in out if x)


def main():
    corpus = [json.loads(line) for line in CORPUS_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
    total_cases = len(corpus)
    print(f"Starting replay test with {total_cases} conversations...")
    print(f"Target: {BASE_URL}")
    print("-" * 60)

    totals = Counter()
    failures = []
    with httpx.Client() as client:
        for idx, case in enumerate(corpus, 1):
            case_id = case['case_id']
            try:
                conversation_id, summary = post_case(client, case)
                status = "OK"
            except Exception as e:
                failures.append({'case_id': case_id, 'error': str(e)})
                totals['request_errors'] += 1
                print(f"[{idx}/{total_cases}] {case_id} ERROR: {str(e)[:50]}")
                continue

            expected_primary = case['gold_label']['primary_practice_area']
            actual_primary = summary.get('primary_practice_area')
            if actual_primary == expected_primary:
                totals['primary_match'] += 1
            else:
                failures.append({'case_id': case_id, 'type': 'primary', 'expected': expected_primary, 'actual': actual_primary, 'conversation_id': conversation_id})

            expected_cross = case['gold_label']['cross_practice_flag']
            actual_cross = bool(summary.get('cross_practice_flag'))
            if actual_cross == expected_cross:
                totals['cross_match'] += 1
            else:
                failures.append({'case_id': case_id, 'type': 'cross_flag', 'expected': expected_cross, 'actual': actual_cross, 'conversation_id': conversation_id})

            expected_secondary = norm_secondary(case['gold_label']['secondary_practice_areas'])
            actual_secondary = norm_secondary(summary.get('secondary_practice_areas', []))
            if expected_secondary == actual_secondary:
                totals['secondary_exact'] += 1
            else:
                failures.append({'case_id': case_id, 'type': 'secondary', 'expected': expected_secondary, 'actual': actual_secondary, 'conversation_id': conversation_id})

            expected_reco = case['expected_agent_recommendation']
            actual_reco = summary.get('agent_recommendation')
            if actual_reco == expected_reco:
                totals['recommendation_match'] += 1
            else:
                failures.append({'case_id': case_id, 'type': 'recommendation', 'expected': expected_reco, 'actual': actual_reco, 'conversation_id': conversation_id})

            totals['total'] += 1

            # Print progress every case
            success_count = totals['total']
            error_count = totals['request_errors']
            primary_acc = (totals['primary_match'] / success_count * 100) if success_count else 0
            reco_acc = (totals['recommendation_match'] / success_count * 100) if success_count else 0
            print(f"[{idx}/{total_cases}] {case_id} {status} | Success: {success_count} | Errors: {error_count} | Primary: {primary_acc:.1f}% | Reco: {reco_acc:.1f}%")

    print("-" * 60)
    print(f"Replay test complete!")
    print(f"Processed: {totals['total']}/{total_cases} | Errors: {totals['request_errors']}")
    print("-" * 60)

    report = {
        'total': totals['total'],
        'primary_accuracy': round(totals['primary_match'] / totals['total'], 4) if totals['total'] else 0.0,
        'cross_flag_accuracy': round(totals['cross_match'] / totals['total'], 4) if totals['total'] else 0.0,
        'secondary_exact_accuracy': round(totals['secondary_exact'] / totals['total'], 4) if totals['total'] else 0.0,
        'recommendation_accuracy': round(totals['recommendation_match'] / totals['total'], 4) if totals['total'] else 0.0,
        'request_errors': totals['request_errors'],
        'failures_sample': failures[:25],
    }
    out = Path(__file__).with_name('replay_results.json')
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print("\nFinal Results:")
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
