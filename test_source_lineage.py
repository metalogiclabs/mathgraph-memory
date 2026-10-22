import unittest
from source_lineage import lineage_rank

def row(i,text):return {'id':str(i),'content':text}

class LineageTests(unittest.TestCase):
    def test_preservation_does_not_invalidate(self):
        rows=[row(1,'LIB-A fixes cache'),row(2,'LIB-B preserves LIB-A')]
        self.assertEqual(lineage_rank('current status of LIB-A',rows),lineage_rank('current status of LIB-A',rows))
    def test_supersession_not_newer_timestamp(self):
        rows=[row(1,'LIB-A implementation details details'),row(2,'LIB-B supersedes LIB-A'),row(3,'2026-10-22 LIB-A documentation update')]
        out=lineage_rank('current LIB-A implementation details',rows)
        self.assertEqual(out[0][1]['id'],'2')
    def test_historical_retrievable(self):
        rows=[row(1,'LIB-A implementation details details'),row(2,'LIB-B supersedes LIB-A')]
        self.assertEqual(lineage_rank('historical LIB-A implementation details',rows)[0][1]['id'],'1')
    def test_unrelated_and_nonexplicit_no_inference(self):
        rows=[row(1,'LIB-A details'),row(2,'LIB-B newest release'),row(3,'LIB-C supersedes LIB-D')]
        self.assertEqual(lineage_rank('current LIB-A details',rows),lineage_rank('current LIB-A details',rows))
if __name__=='__main__':unittest.main()