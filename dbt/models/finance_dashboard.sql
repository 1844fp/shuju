{{ config(materialized='view', schema='ads') }}
select *, revenue-cost as gross_profit, revenue-cost-expense as operating_profit,
(revenue-cost)/nullif(revenue,0) as gross_margin
from {{ ref('finance_monthly') }}
