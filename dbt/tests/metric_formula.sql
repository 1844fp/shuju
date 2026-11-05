select * from {{ ref('finance_dashboard') }}
where operating_profit <> revenue-cost-expense
or (revenue=0 and gross_margin is not null)
