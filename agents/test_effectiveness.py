import json,os,unittest
from unittest.mock import patch
from agents.provider import Provider
from agents.semantic import Semantic

class EffectivenessTests(unittest.TestCase):
    def test_explicit_unsupported_intent(self):
        transport=lambda _: {'choices':[{'message':{'content':json.dumps({'intent':'unsupported','reason':'unsupported_operation'})}}]}
        with patch.dict(os.environ,dict(FINAGENT_MODEL_API_KEY='test-only',FINAGENT_MODEL='test-only',FINAGENT_MODEL_BASE_URL='https://invalid.test')):
            with self.assertRaisesRegex(ValueError,'^unsupported_model_request$'):Provider(transport=transport).plan('立即付款')

    def test_fiscal_year_and_metric_constraints(self):
        class Model:
            max_seq_length=128
            def encode(self,texts,**kwargs):
                # Equal semantic scores make the precise fiscal/metric boundary discriminating.
                class Vector:
                    def __matmul__(self,other):return 1.
                return [Vector() for _ in texts]
        s=Semantic();s.model=Model();s.provenance={'revision':'fixture'}
        docs=[dict(id='a',title='MSFT FY2024 operating_profit',text='2024 财年经营利润',effective_date='2025-01-01',version='1'),dict(id='b',title='MSFT FY2025 net_income',text='2025 财年净利润',effective_date='2025-01-01',version='1'),dict(id='c',title='MSFT FY2025 operating_profit',text='2025 财年经营利润',effective_date='2025-01-01',version='1')]
        hits=s.search('微软2025财年经营利润是多少',docs)
        self.assertEqual(hits[0]['id'],'c')
        self.assertNotIn('a',[x['id'] for x in hits])
        self.assertEqual(s.search('FY2023 operating income',docs),[])

if __name__=='__main__':unittest.main()
