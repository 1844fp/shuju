"""Deterministic risk leads over an authorized, single-organization snapshot.

Caller must enforce authorization and supply stable evidence IDs; no database,
model, posting or payment access. Missing fields never mean a clean bill of health.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

VERSION = 'finance-risk-1.0'
RULES = ('duplicate_expense', 'large_amount', 'split_expense', 'weekend',
         'new_supplier', 'budget_exceeded', 'unbalanced_voucher', 'expense_growth')


def money(value):
    if isinstance(value, (float, bool)):
        raise ValueError('Amounts must be decimal strings, not floats')
    try:
        result = Decimal(value)
        if not result.is_finite() or abs(result) > Decimal('999999999999999999.99') or result != result.quantize(Decimal('.01')):
            raise ValueError('Invalid amount precision or range')
        return result
    except (InvalidOperation, TypeError):
        raise ValueError('Invalid decimal amount') from None


def evaluate(records, currency, large_threshold='10000.00', split_threshold='10000.00'):
    """Rows require id, currency, date; optional fields enable individual rules.

    budget and previous_amount describe comparable department-period totals,
    not per-line allocations. Split detection is same employee/day/currency,
    2+ positive claims below threshold whose sum reaches threshold. New supplier
    means within 30 calendar days of registration. Growth threshold is 50%.
    """
    large, split = money(large_threshold), money(split_threshold)
    if large <= 0 or split <= 0 or not isinstance(currency, str) or len(currency) != 3:
        raise ValueError('Invalid thresholds or currency')
    rows = list(records)
    if len(rows) > 10000:
        raise ValueError('At most 10000 records')
    ids = set()
    for row in rows:
        if not row.get('id') or row['id'] in ids:
            raise ValueError('Evidence IDs must be present and unique')
        ids.add(row['id'])
        if row.get('currency') != currency:
            raise ValueError('Currency mixing is prohibited')
        date.fromisoformat(row['date'])
        for key in ('amount', 'budget', 'previous_amount', 'debit', 'credit'):
            if key in row: money(row[key])
    outputs = {rule: dict(rule=rule, rule_version=VERSION, evaluated_ids=[], findings=[]) for rule in RULES}
    def check(rule, group, hit, explanation):
        output = outputs[rule]
        evidence = sorted(r['id'] for r in group)
        output['evaluated_ids'].extend(evidence)
        if hit: output['findings'].append(dict(evidence_ids=evidence, explanation=explanation, classification='risk_lead'))
    duplicates, splits, vouchers = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        day = date.fromisoformat(row['date'])
        check('weekend', [row], day.weekday() >= 5, '周末记录需结合企业工作日历复核')
        if 'amount' in row:
            amount = money(row['amount'])
            check('large_amount', [row], abs(amount) > large, '绝对金额超过配置阈值')
            if row.get('employee') and row.get('invoice'):
                duplicates[(row['employee'], row['invoice'], row['date'], amount)].append(row)
            if row.get('employee'):
                splits[(row['employee'], row['date'])].append(row)
            if row.get('supplier') and row.get('supplier_created'):
                age = (day - date.fromisoformat(row['supplier_created'])).days
                check('new_supplier', [row], 0 <= age <= 30 and amount > large, '注册30日内供应商大额记录')
            if row.get('department') and 'budget' in row:
                check('budget_exceeded', [row], amount > money(row['budget']), '部门期间实际超过明确预算')
            if row.get('department') and 'previous_amount' in row:
                previous = money(row['previous_amount'])
                if previous > 0:
                    check('expense_growth', [row], amount > previous * Decimal('1.5'), '可比期间部门费用增长超过50%')
        if row.get('voucher_id') and 'debit' in row and 'credit' in row:
            vouchers[(row['date'][:7], row['voucher_id'])].append(row)
    for group in duplicates.values(): check('duplicate_expense', group, len(group) > 1, '员工、发票号、日期与金额重复')
    for group in splits.values():
        eligible = [r for r in group if 0 < money(r['amount']) < split]
        check('split_expense', group, len(eligible) > 1 and sum((money(r['amount']) for r in eligible), Decimal(0)) >= split, '同员工同日多笔阈值以下申报累计达到阈值；需人工核对业务原因')
    for group in vouchers.values():
        check('unbalanced_voucher', group, sum((money(r['debit']) - money(r['credit']) for r in group), Decimal(0)) != 0, '所提供凭证行借贷不平；须确认快照完整性')
    for output in outputs.values():
        output['evaluated_ids'] = sorted(set(output['evaluated_ids']))
        output['status'] = 'evaluated' if output['evaluated_ids'] else 'not_evaluated'
        output['missing_ids'] = sorted(ids - set(output['evaluated_ids']))
    return dict(rule_version=VERSION, currency=currency, rules=list(outputs.values()), basis='风险线索非舞弊结论；调用方须保证组织权限和输入范围完整')
