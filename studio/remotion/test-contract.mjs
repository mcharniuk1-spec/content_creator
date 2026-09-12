import test from 'node:test';
import assert from 'node:assert/strict';
import {alignmentPlanHash, validateEDL} from './contract.mjs';
const fixture = () => ({schema:'m2.remotion-edl.v1',fps:30,width:1080,height:1920,duration_frames:60,render_mode:'PREVIS',review_state:'REVIEW_PENDING',assets:[],captions:[{from_frame:0,duration_frames:60,text:'A test'}],audio_stems:[],scenes:[{scene_id:'s1',from_frame:0,duration_frames:60,layout:'motion_graphic',layers:[{kind:'graphic',text:'A deterministic fixture'}]}]});
test('valid preview',()=>assert.equal(validateEDL(fixture()).duration_frames,60));
test('timeline gaps fail',()=>{const e=fixture();e.scenes[0].from_frame=1;assert.throws(()=>validateEDL(e),/PARTITION/);});
test('production approval gate',()=>assert.throws(()=>validateEDL(fixture(),{production:true}),/APPROVED/));
test('remote and traversal assets fail',()=>{for(const p of ['https://example.com/a.mp4','../a.mp4']){const e=fixture();e.assets=[{asset_id:'a',kind:'video',path:p,sha256:'a'.repeat(64),rights_approved:true,rights_receipt_id:'r'}];assert.throws(()=>validateEDL(e),/PATH/);}});
test('out-of-range captions fail',()=>{const e=fixture();e.captions[0].duration_frames=61;assert.throws(()=>validateEDL(e),/CAPTION/);});
test('production cannot render pending footage',()=>{const e=fixture();e.render_mode='PRODUCTION';e.review_state='APPROVED';e.scenes[0].layers=[{kind:'placeholder',text:'pending'}];assert.throws(()=>validateEDL(e,{production:true}),/PENDING/);});
const productionFixture=()=>{const e=fixture();e.render_mode='PRODUCTION';e.review_state='APPROVED';e.scenes[0].layers=[{kind:'text',text:'Approved editable title'}];e.speech_policy='NO_SPEECH';e.pending_audio_assets=[];e.source_card_hash='c'.repeat(64);return e;};
test('production rejects pending narration and unbuilt graphics',()=>{const e=productionFixture();validateEDL(e,{production:true});e.pending_audio_assets=['voice'];assert.throws(()=>validateEDL(e,{production:true}),/AUDIO_RECORDING_OR_PLACEMENT_PENDING/);e.pending_audio_assets=[];e.scenes[0].layers=[{kind:'graphic',text:'Build this diagram later'}];assert.throws(()=>validateEDL(e,{production:true}),/UNBUILT_GRAPHIC_PLAN/);});
test('required narration needs content-bound reviewed alignment',()=>{const e=productionFixture();e.speech_policy='REQUIRED_RECORDED_SPEECH';assert.throws(()=>validateEDL(e,{production:true}),/RECORDED_SPEECH_STEM_REQUIRED/);e.assets=[{asset_id:'voice',kind:'audio',path:'voice.wav',sha256:'a'.repeat(64),rights_approved:true,rights_receipt_id:'rights',duration_frames:60}];e.audio_stems=[{asset_id:'voice',role:'speech',from_frame:0,duration_frames:60,volume:1}];assert.throws(()=>validateEDL(e,{production:true}),/ALIGNMENT_REQUIRED/);e.speech_alignment={review_state:'APPROVED',receipt_id:'alignment',source_card_hash:e.source_card_hash,audio_asset_hashes:{voice:'a'.repeat(64)},alignment_plan_sha256:alignmentPlanHash(e)};validateEDL(e,{production:true});e.assets[0].sha256='b'.repeat(64);assert.throws(()=>validateEDL(e,{production:true}),/ALIGNMENT_REQUIRED/);});

test('alignment approval rejects changed placement trim gain and captions',()=>{
  const e=productionFixture(); e.speech_policy='REQUIRED_RECORDED_SPEECH';
  e.assets=[{asset_id:'voice',kind:'audio',path:'voice.wav',sha256:'a'.repeat(64),rights_approved:true,rights_receipt_id:'rights',duration_frames:120}];
  e.audio_stems=[{asset_id:'voice',role:'speech',from_frame:0,duration_frames:30,trim_before_frames:0,volume:.8}];
  e.captions=[{from_frame:0,duration_frames:30,text:'Proof — Пример 🔬'}];
  e.speech_alignment={review_state:'APPROVED',receipt_id:'alignment',source_card_hash:e.source_card_hash,audio_asset_hashes:{voice:'a'.repeat(64)},alignment_plan_sha256:alignmentPlanHash(e)};
  validateEDL(e,{production:true});
  for(const [section,key,value] of [['audio_stems','from_frame',1],['audio_stems','duration_frames',29],['audio_stems','trim_before_frames',1],['audio_stems','volume',.7],['captions','from_frame',1],['captions','duration_frames',29],['captions','text','Changed caption']]) {
    const changed=structuredClone(e); changed[section][0][key]=value;
    assert.throws(()=>validateEDL(changed,{production:true}),/ALIGNMENT_REQUIRED/);
  }
});
