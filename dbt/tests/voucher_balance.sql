select organization_id,voucher_no,posting_date,currency
from dwd.fact_journal_entry
group by organization_id,source_system,voucher_no,posting_date,currency
having sum(debit) <> sum(credit)
