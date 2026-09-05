"""Failure-oriented tests for a reusable local Signal evidence authority."""
import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from m2_signal.engine import _number, analyze, backup_database, connect, file_hash, ingest_export, restore_database
from m2_signal.legacy import import_legacy_db
from m2_signal.metrics import candidate_key, distribution, rate, robust_z, validate_config, wilson


class SignalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root/'source'
        self.source.mkdir()
        self.db = self.root/'signal.sqlite'
        self.rows = [dict(code='CODE'+str(i), user='creator', url='https://www.instagram.com/reel/CODE'+str(i)+'/',
                         play=1000*(i+1), like=30*(i+1), comment=2*(i+1), reshare=3*(i+1), save=None if i==0 else i,
                         duration_s=20, ts=1788200000+i, caption='Original test caption') for i in range(6)]
        self.write_export()

    def tearDown(self):
        self.temp.cleanup()

    def write_export(self, snapshot_date='2026-09-01'):
        with (self.source/'reels.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(self.rows[0])); w.writeheader(); w.writerows(self.rows)
        (self.source/'accounts.csv').write_text('username,followers,media_count,category,biography\ncreator,100,20,test,\n')
        (self.source/'snapshot.json').write_text(json.dumps({'taken':snapshot_date,'accounts':1}))
        (self.source/'transcripts.json').write_text(json.dumps({'CODE0':{'words':2,'segments':[{'s':0,'e':2,'t':'test words'}]}}))
        (self.source/'cuts.json').write_text(json.dumps({'CODE0':{'cuts':3}}))

    def replay(self, output='out', config=None):
        ingest=ingest_export(self.db,self.source,config)
        summary=analyze(self.db,ingest['release_id'],self.root/output)
        return ingest,summary

    def output_rows(self,name='reels'):
        return [json.loads(line) for line in (self.root/'out'/(name+'.jsonl')).read_text().splitlines()]

    def test_complete_replay_is_idempotent_and_null_preserving(self):
        first, summary=self.replay()
        hashes={p.name:file_hash(p) for p in (self.root/'out').iterdir() if p.is_file()}
        second, again=self.replay()
        self.assertEqual(first['release_id'],second['release_id'])
        self.assertEqual(second['new_immutable_records'],0)
        self.assertEqual(summary,again)
        self.assertEqual(hashes,{p.name:file_hash(p) for p in (self.root/'out').iterdir() if p.is_file()})
        code0=self.output_rows()[0]
        self.assertIsNone(code0['saves'])
        self.assertIsNone(code0['saves_per_1k_views'])
        self.assertEqual(summary['population']['source_observations'],6)
        self.assertEqual(summary['coverage']['source_media']['denominator'],6)
        self.assertFalse(summary['evidence_release_accepted'])

    def test_immutable_source_and_analysis_tables_reject_overwrite(self):
        self.replay()
        db=connect(self.db)
        for query in ["UPDATE observations SET payload_json='{}'",'DELETE FROM observations',
                      "UPDATE reel_analysis SET payload_json='{}'",'DELETE FROM releases']:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(query)
        db.close()

    def test_growing_export_reuses_unchanged_values_but_retains_old_release(self):
        first,_=self.replay()
        self.rows.append(dict(self.rows[-1],code='NEWCODE',play=7500))
        self.write_export()
        second,new=self.replay('out2')
        self.assertNotEqual(first['release_id'],second['release_id'])
        self.assertEqual(second['new_immutable_records'],1)
        self.assertEqual(new['population']['canonical_reels'],7)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM reel_analysis WHERE release_id=?',(first['release_id'],)).fetchone()[0],6)

    def test_second_snapshot_keeps_changed_and_unchanged_capture_observations(self):
        first,_=self.replay()
        self.rows[0]['play']=9999
        self.write_export('2026-09-02')
        second,_=self.replay('out2')
        with sqlite3.connect(self.db) as db:
            rows=db.execute("SELECT snapshot_date,payload_json FROM observations WHERE kind='reels' AND entity_key='CODE0' ORDER BY snapshot_date").fetchall()
            self.assertEqual([json.loads(r[1])['play'] for r in rows],['1000','9999'])
        self.assertNotEqual(first['release_id'],second['release_id'])

    def test_conflicting_identity_quarantines_all_members_and_keeps_observations(self):
        self.rows.append(dict(self.rows[0],user='different',play=3000))
        self.write_export()
        _,summary=self.replay()
        self.assertEqual(summary['population']['source_observations'],7)
        self.assertEqual(summary['population']['canonical_reels'],6)
        row=self.output_rows()[0]
        self.assertIsNone(row['account_username'])
        self.assertEqual(row['source_row_count'],2)
        self.assertEqual(row['eligibility_state'],'FAIL')
        self.assertIsNone(row['diagnostic_equal_weight_z'])
        self.assertEqual(len(row['observation_ids']),2)

    def test_identical_duplicate_preserves_membership_without_false_conflict(self):
        self.rows.append(dict(self.rows[0]))
        self.write_export()
        _,summary=self.replay()
        self.assertEqual(summary['population']['identity_conflict_groups'],0)
        self.assertEqual(self.output_rows()[0]['source_row_count'],2)
        self.assertEqual(len(self.output_rows()[0]['observation_ids']),1)

    def test_invalid_zero_views_positive_actions_and_nonfinite_values_block(self):
        self.rows[0]['play']=0
        self.rows[1]['play']='NaN'
        self.rows[2]['like']=-1
        self.rows[3]['comment']='1.5'
        self.write_export()
        _,summary=self.replay()
        self.assertEqual(summary['population']['quarantined_reels'],4)
        for row in self.output_rows()[:4]:
            self.assertEqual(row['eligibility_state'],'FAIL')
            self.assertIsNone(row['diagnostic_equal_weight_z'])

    def test_insufficient_baseline_has_null_hit_and_coverage_denominator(self):
        self.rows=self.rows[:2]
        self.write_export()
        self.replay()
        account=self.output_rows('accounts')[0]
        self.assertIsNone(account['hit_rate'])
        self.assertIsNone(account['transcript_coverage'])
        self.assertIsNone(account['distributions']['views']['coverage'])

    def test_media_inventory_is_not_decoded_scene_evidence(self):
        (self.source/'CODE0.mp4').write_bytes(b'not an actual video')
        _,summary=self.replay()
        self.assertEqual(summary['coverage']['source_media']['observed_or_partial'],1)
        self.assertEqual(summary['coverage']['semantic_scenes']['observed_or_partial'],0)
        attempts=self.output_rows('evidence-attempts')
        self.assertFalse(any(a['media_decoded'] for a in attempts))
        scene=next(a for a in attempts if a['reel_id']=='instagram:CODE0' and a['modality']=='semantic_scenes')
        self.assertEqual(scene['reason_code'],'MEDIA_DECODE_AND_SCENE_REVIEW_NOT_RUN')

    def test_backup_restore_integrity_counts_and_append_only_constraints(self):
        self.replay()
        backup=self.root/'backup.sqlite'; restored=self.root/'restored.sqlite'
        self.assertEqual(backup_database(self.db,backup)['stage_state'],'PASS')
        restore_database(backup,restored)
        with sqlite3.connect(self.db) as src, sqlite3.connect(restored) as dst:
            for table in ['releases','observations','release_observations','reel_analysis','account_analysis','evidence_attempts','metric_observations','reel_metric_values']:
                self.assertEqual(src.execute('SELECT * FROM '+table+' ORDER BY 1,2').fetchall(),dst.execute('SELECT * FROM '+table+' ORDER BY 1,2').fetchall())
            self.assertEqual(dst.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            with self.assertRaises(sqlite3.IntegrityError):
                dst.execute('DELETE FROM observations')
        with self.assertRaises(ValueError):
            restore_database(backup,restored)

    def test_source_alias_ambiguity_rejected(self):
        (self.source/'ролики.csv').write_bytes((self.source/'reels.csv').read_bytes())
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            ingest_export(self.db,self.source)

    def test_snapshot_csv_count_disagreement_rejected_before_ingest(self):
        (self.source/'snapshot.json').write_text(json.dumps({'taken':'2026-09-01','accounts':1,'rows':[]}))
        with self.assertRaisesRegex(ValueError,'observation count mismatch'):
            ingest_export(self.db,self.source)
        self.assertFalse(self.db.exists())

    def test_different_config_cannot_replace_existing_analysis_output(self):
        self.replay()
        second=ingest_export(self.db,self.source,{'absolute_exposure_floor':2000})
        with self.assertRaisesRegex(ValueError,'another immutable release'):
            analyze(self.db,second['release_id'],self.root/'out')

    def test_implementation_tamper_requires_new_release(self):
        receipt,_=self.replay()
        with patch('m2_signal.engine.implementation_hash',return_value='changed'):
            with self.assertRaisesRegex(ValueError,'implementation changed'):
                analyze(self.db,receipt['release_id'],self.root/'out')

    def test_network_and_unknown_platform_admission_rejected(self):
        for overrides in [{'collection_enabled':True},{'platform':'youtube'},{'unexpected':2},{'z_clip':float('nan')},{'minimum_components':6}]:
            with self.assertRaises(ValueError):
                validate_config(overrides)

    def test_math_oracles_and_coverage_first_selection(self):
        self.assertEqual(_number('9007199254740993', integer=True),(9007199254740993,None))
        self.assertIsNotNone(_number('9223372036854775808', integer=True)[1])
        self.assertIsNotNone(_number(True, integer=True)[1])
        self.assertIsNone(rate(None,100))
        self.assertEqual(rate(3,1500),2)
        self.assertIsNone(rate(3,0))
        low,high=wilson(5,10)
        self.assertAlmostEqual(low,.23659309,places=7)
        self.assertAlmostEqual(high,.76340691,places=7)
        self.assertEqual(robust_z(5,[1,2,3,4,5],kind='log_views',config=validate_config()),1.3489795)
        self.assertEqual(distribution([1,None,3,5],4)['coverage'],.75)
        complete={'diagnostic_component_count':5,'diagnostic_equal_weight_z':0,'published_epoch_seconds':1,'views':100,'code':'A'}
        partial=dict(complete,diagnostic_component_count=4,diagnostic_equal_weight_z=5,code='B')
        self.assertEqual(max([complete,partial],key=candidate_key)['code'],'A')


class LegacyAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.db=self.root/'legacy#source.sqlite'
        with sqlite3.connect(self.db) as db:
            db.executescript('''
              CREATE TABLE snapshots(id INTEGER,taken TEXT,accounts_n INTEGER,reels_n INTEGER,done INTEGER);
              CREATE TABLE reels(snapshot_id INTEGER,code TEXT,username TEXT,ts INTEGER,play INTEGER,likes INTEGER,comm INTEGER,resh INTEGER,save INTEGER,dur REAL,cap TEXT,followers INTEGER);
              CREATE TABLE accounts(username TEXT,follower_count INTEGER,media_count INTEGER,category TEXT,biography TEXT);
              CREATE TABLE transcripts(code TEXT,lang TEXT,words INTEGER,segments TEXT);
              CREATE TABLE deepdives(snapshot_id INTEGER,code TEXT,cuts INTEGER);
              CREATE TABLE topics(code TEXT,topic TEXT);
              CREATE TABLE spend(secret TEXT);
              INSERT INTO snapshots VALUES(1,'2026-09-01',1,1,1),(2,'2026-09-02',1,1,0);
              INSERT INTO reels VALUES(1,'CODEA','creator',1788200000,2000,50,2,3,NULL,20,'test',900);
              INSERT INTO accounts VALUES('creator',1000,20,'test','');
              INSERT INTO transcripts VALUES('CODEA','en',2,'[{"s":0,"e":2,"t":"test words"}]');
              INSERT INTO deepdives VALUES(1,'CODEA',3);
              INSERT INTO spend VALUES('DO_NOT_EXPORT_PRIVATE_SENTINEL');
            ''')

    def tearDown(self):
        self.temp.cleanup()

    def test_read_only_allowlist_null_horizon_and_idempotence(self):
        before=file_hash(self.db)
        out=self.root/'export'
        receipt=import_legacy_db(self.db,out,'2026-09-01')
        self.assertEqual(receipt,import_legacy_db(self.db,out,'2026-09-01'))
        self.assertEqual(before,file_hash(self.db))
        self.assertNotIn('DO_NOT_EXPORT_PRIVATE_SENTINEL',''.join(p.read_text() for p in out.iterdir()))
        newdb=self.root/'signal.sqlite'
        ing=ingest_export(newdb,out)
        summary=analyze(newdb,ing['release_id'],self.root/'analysis')
        self.assertEqual(summary['population']['canonical_reels'],1)
        row=json.loads((self.root/'analysis/reels.jsonl').read_text())
        self.assertIsNone(row['saves']); self.assertIsNone(row['observed_at'])
        self.assertIn('CURRENT_DB_NOT_HISTORICAL_SNAPSHOT',(out/'accounts.csv').read_text())
        self.assertFalse(receipt['collection_executed'])

    def test_incomplete_snapshot_and_unknown_date_blocked(self):
        for taken in ('2026-09-02','2026-09-03'):
            with self.assertRaisesRegex(ValueError,'completed snapshot'):
                import_legacy_db(self.db,self.root/'no-output',taken)
        self.assertFalse((self.root/'no-output').exists())

    def test_mutated_source_cannot_overwrite_export(self):
        out=self.root/'export'
        import_legacy_db(self.db,out,'2026-09-01')
        with sqlite3.connect(self.db) as db:
            db.execute('UPDATE reels SET play=2500')
        with self.assertRaisesRegex(ValueError,'immutable export target'):
            import_legacy_db(self.db,out,'2026-09-01')


if __name__ == '__main__':
    unittest.main()
