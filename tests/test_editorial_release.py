"""Release-specific integration checks; no provider, model or network access."""
import hashlib
import json
from pathlib import Path
import unittest

from m2_orchestrator.state import implementation_manifest
from m2_studio.media import StudioError
from m2_studio.timeline import build_card_edl, validate_edl

ROOT = Path(__file__).resolve().parents[1]
SLATE = ROOT / 'examples/ten-card-20260907'

class EditorialReleaseTests(unittest.TestCase):
    def test_slate_and_asset_integrity(self):
        manifest = json.loads((SLATE / 'manifest.json').read_text())
        self.assertEqual(len(manifest['cards']), 10)
        groups = {'introduction': [], 'regular': []}
        for entry in manifest['cards']:
            path = SLATE / (entry['card_id'] + '.json')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['card_sha256'])
            card = json.loads(path.read_text())
            groups[card['publication_group']].append(card)
            image = SLATE / card['storyboard']['path']
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), entry['storyboard_sha256'])
            self.assertEqual(image.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(card['source_candidate_sha256'], manifest['source_candidate_sha256'])
            self.assertEqual(' '.join(s['spoken_text'] for s in card['segments']), card['full_spoken_english'])
        for cards in groups.values():
            self.assertEqual(len(cards), 5)
            self.assertTrue(any(c['synthesis'] and c['source_reference_count'] > 1 for c in cards))

    def test_every_card_compiles_to_planned_timeline(self):
        for path in SLATE.glob('M2-*.json'):
            card = json.loads(path.read_text())
            edl = build_card_edl(card)
            validate_edl(edl)
            self.assertEqual(len(edl['scenes']), 7)
            self.assertEqual(sum(s['duration_frames'] for s in edl['scenes']), 1800)
            self.assertEqual(edl['render_mode'], 'PREVIS')
            self.assertEqual(edl['speech_policy'], 'REQUIRED_RECORDED_SPEECH')
            self.assertFalse(edl['provider_execution'])
            self.assertTrue(edl['pending_audio_assets'])
            self.assertEqual(' '.join(s['text'] for s in edl['captions']), card['full_spoken_english'])
            with self.assertRaises(StudioError):
                validate_edl(edl, production=True)
            edl.update(render_mode='PRODUCTION', review_state='APPROVED')
            with self.assertRaises(StudioError):
                validate_edl(edl, production=True)

    def test_new_editorial_dependencies_are_hash_bound(self):
        bound = implementation_manifest()
        for path in ['skills/humanize-writing/SKILL.md', 'knowledge/studio/creator-techniques-20260907.md']:
            self.assertEqual(bound[path], hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        roles = json.loads((ROOT / 'agents/m2-roles.json').read_text())['roles']
        for role in roles:
            if role['role'] in ['script_architect', 'scene_planner', 'studio_reviewer']:
                self.assertIn('skills/humanize-writing/SKILL.md', role['role_context'])

if __name__ == '__main__':
    unittest.main()
