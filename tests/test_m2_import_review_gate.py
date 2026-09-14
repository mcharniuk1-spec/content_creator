import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from import_m2_shared import validate_independent_review

class ReviewGateTests(unittest.TestCase):
    def test_accepted_hashes_do_not_replace_independent_actors(self):
        valid={'status':'ACCEPTED_MECHANICAL_RECONCILIATION_ONLY','maker':'maker','reviewer':'reviewer','reviewed_artifact_hashes':{'packet':'a'*64}}
        validate_independent_review(valid)
        for fields in [{'maker':None},{'reviewer':None},{'maker':''},{'reviewer':' '},{'maker':'reviewer'},{'maker':' reviewer '},{'reviewer':['reviewer']},{'status':'candidate'}]:
            with self.subTest(fields=fields),self.assertRaisesRegex(ValueError,'INDEPENDENT_REVIEW_REQUIRED'):
                validate_independent_review(valid|fields)
