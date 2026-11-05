{{ config(materialized='view', schema='dws') }}
select * from dws.monthly_finance
