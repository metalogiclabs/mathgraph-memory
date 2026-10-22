import unittest
from adversarial_eval import evaluate
from temporal_rank import temporal_rank
class TemporalTests(unittest.TestCase):
 def test_adversarial_seed(self):
  result=evaluate();self.assertEqual(result['overall']['temporal']['correct'],240)
  self.assertEqual(result['overall']['lexical']['correct'],120)
 def test_no_date_retains_lexical(self):
  rows=[{'id':'a','content':'alpha alpha','created_at':'2026-01-01'}, {'id':'b','content':'beta','created_at':'2026-01-02'}]
  self.assertEqual(temporal_rank('alpha',rows)[0][1]['id'],'a')
 def test_missing_date_fallback(self):
  rows=[{'id':'a','content':'alpha','created_at':'2026-01-01'}]
  self.assertEqual(len(temporal_rank('latest alpha',rows)),1)
if __name__=='__main__':unittest.main()