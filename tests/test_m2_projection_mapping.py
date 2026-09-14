import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('projection', Path(__file__).parents[1]/'scripts/project_m2_evidence.py')
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class ProjectionMappingTests(unittest.TestCase):
    def record(self, table, payload, key='1'):
        return ('a'*64, table, key, projection.digest(payload), payload)

    def test_distinct_counters_and_date(self):
        products, gaps = projection.project_records([
            self.record('snapshots', {'id': 7, 'taken': '2026-09-14'}),
            self.record('reels', {'code': 'fixture1234', 'snapshot_id': 7, 'play': 0, 'save': None, 'resh': 4, 'comm': 2})])
        m = products['metrics'][0]
        self.assertEqual((m['views'], m['saves'], m['reshares'], m['sends']), (0, None, 4, None))
        self.assertEqual((m['snapshot_taken'], m['capture_precision']), ('2026-09-14', 'date'))
        self.assertEqual(gaps, [])

    def test_invalid_counter_quarantines_projection(self):
        products, gaps = projection.project_records([self.record('reels', {'code': 'fixture1234', 'save': ''})])
        self.assertEqual(products['metrics'], [])
        self.assertEqual(gaps[0]['reason'], 'INVALID_NONNEGATIVE_NUMBER')
        self.assertEqual(len(products['lineage']), 1)

    def test_original_text_and_bad_segments_separate(self):
        p, gaps = projection.project_records([self.record('transcripts', {'code': 'fixture1234', 'lang': 'en', 'text': 'Original. ', 'segments': '[{"start": 4, "end": 2, "text":"bad"}]'})])
        self.assertEqual(p['transcripts'][0]['original_text'], 'Original. ')
        self.assertEqual(p['transcripts'][0]['segments_parse_state'], 'invalid')
        self.assertEqual(p['transcripts'][0]['state'], 'source_text_unreviewed')
        self.assertEqual(p['segments'], [])

    def test_source_version_preserved(self):
        rows = [self.record('transcripts', {'code': 'fixture1234', 'text': value}, str(i)) for i, value in enumerate(['one', 'two'])]
        products, _ = projection.project_records(rows)
        self.assertEqual(len(products['transcripts']), 2)
        self.assertNotEqual(products['transcripts'][0]['lineage_id'], products['transcripts'][1]['lineage_id'])

    def test_declared_frame_never_verifies_bytes(self):
        products, _ = projection.project_records([self.record('frames', {'code':'fixture1234','idx':0,'t_sec':1.2,'path':'missing.jpg','exists_ok':1,'sha256':'b'*64})])
        self.assertEqual(len(products['frame_pointers']), 1)
        self.assertNotIn('asset_checks', products)

    def test_retained_original_full_text_and_separate_segments(self):
        products, _ = projection.project_records([
            self.record('transcripts', {'code':'fixture1234','part':1,'original_full_text':'Retained original.','detected_language':'en'}),
            self.record('transcript_segments', {'code':'fixture1234','part':1,'sequence':1,'start_seconds':0,'end_seconds':2,'original_segment_text':'Retained original.'})])
        self.assertEqual(products['transcripts'][0]['state'], 'source_text_unreviewed')
        self.assertEqual(products['transcripts'][0]['original_text'], 'Retained original.')
        self.assertEqual(products['segments'][0]['original_text'], 'Retained original.')


if __name__ == '__main__':
    unittest.main()
