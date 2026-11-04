"""Reproduce the report's illustrative USD scenarios; no provider calls."""
import csv
from decimal import Decimal as D
from pathlib import Path


def contribution(p, rail=D('.001'), judge=D('.001055'), support=D('.005'), loss=D('.01')):
    return D('.05') * p - rail - judge - support - loss * p


def main():
    judge = (D(3000) * D('.20') + D(500) * D('.80')) / D(1000000) * D('1.055')
    assert judge == D('.001055')
    assert contribution(D('.05')) == D('-.005055')
    assert contribution(D('.20')) == D('.000945')
    assert contribution(D('1')) == D('.032945')
    assert contribution(D('5')) == D('.192945')
    base = (D('.001') + judge + D('.005')) / D('.04')
    assert base == D('.176375')
    assert contribution(base) == 0
    assert contribution(base - D('.000001')) < 0
    assert contribution(base + D('.000001')) > 0
    selective = (D('.001') + judge / 10 + D('.005')) / D('.04')
    batched = (D('.001') / 100 + judge + D('.005')) / D('.04')
    combined = (D('.001') / 100 + judge / 10 + D('.005')) / D('.04')
    assert selective == D('.1526375')
    assert batched == D('.151625')
    assert combined == D('.1278875')
    assert max(D('.05') * D('.05'), D('.01')) == D('.01')
    assert (D(30000) - D(1000)) * D('.001') == 29
    rows = []
    for p in map(D, ['.05', '.20', '1', '5']):
        rows.append([p, D('.05') * p, D('.001'), judge, D('.01') * p,
                     D('.005'), contribution(p), contribution(p) * 1000,
                     max(D('.05') * p, D('.01'))])
    path = Path(__file__).with_name('micro-job-economics.csv')
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['price_usd', 'fee_usd', 'rail_usd', 'judge_usd',
                         'estimated_dispute_loss_usd', 'estimated_support_usd',
                         'contribution_usd', 'contribution_1000_jobs_usd',
                         'refundable_deposit_usd'])
        writer.writerows(rows)
    print('PASS: four prices, break-even boundary, three sensitivities, deposit, monthly tier')


if __name__ == '__main__':
    main()
