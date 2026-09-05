// Runtime validation is mandatory even for callers bypassing the Python adapter.
import {createHash} from 'node:crypto';

export function alignmentPlanHash(edl) {
  const stems = edl.audio_stems ?? [], used = new Set(stems.map(s => s.asset_id));
  const gain = value => {const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return bytes.toString('hex');};
  const plan = {
    schema: 'm2.speech-alignment-plan.v1', source_card_hash: edl.source_card_hash ?? null,
    fps: edl.fps, duration_frames: edl.duration_frames, speech_policy: edl.speech_policy ?? null,
    audio_asset_hashes: Object.fromEntries((edl.assets ?? []).filter(a => used.has(a.asset_id)).map(a => [a.asset_id, a.sha256])),
    audio_stems: stems.map(s => ({asset_id:s.asset_id, role:s.role, from_frame:s.from_frame,
      duration_frames:s.duration_frames, trim_before_frames:s.trim_before_frames ?? 0, volume_float64_hex:gain(s.volume ?? 1)})),
    captions: (edl.captions ?? []).map(c => ({from_frame:c.from_frame, duration_frames:c.duration_frames, text:c.text})),
  };
  const ordered = v => Array.isArray(v) ? v.map(ordered) : v !== null && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, ordered(v[k])])) : v;
  return createHash('sha256').update(JSON.stringify(ordered(plan)), 'utf8').digest('hex');
}

export function validateEDL(edl, {production = false} = {}) {
  const fail = code => {throw new Error(code);};
  const int = Number.isInteger;
  if (edl.schema !== 'm2.remotion-edl.v1') fail('INVALID_EDL_SCHEMA');
  if (![24,25,30,50,60].includes(edl.fps) || !int(edl.duration_frames) || edl.duration_frames < 1 || edl.duration_frames > edl.fps * 600) fail('INVALID_EDL_TIMEBASE');
  if (![540,1080,1920].includes(edl.width) || ![960,1080,1920].includes(edl.height)) fail('INVALID_EDL_RESOLUTION');
  if (!['PREVIS','PRODUCTION'].includes(edl.render_mode)) fail('INVALID_RENDER_MODE');
  if (production && (edl.review_state !== 'APPROVED' || edl.render_mode !== 'PRODUCTION')) fail('EDIT_NOT_APPROVED');
  const assetMap = new Map();
  for (const a of edl.assets ?? []) {
    if (assetMap.has(a.asset_id)) fail('DUPLICATE_ASSET_ID');
    if (!['video','image','audio'].includes(a.kind)) fail('UNSUPPORTED_ASSET_KIND');
    if (a.rights_approved !== true || !a.rights_receipt_id) fail('ASSET_RIGHTS_MISSING');
    if (!/^[a-f0-9]{64}$/.test(a.sha256)) fail('ASSET_HASH_MISSING');
    if (typeof a.path !== 'string' || !a.path || /[:\\]/.test(a.path) || a.path.startsWith('/') || a.path.split('/').includes('..')) fail('PATH_OUTSIDE_ALLOWLIST');
    if (!/\.(png|jpg|jpeg|webp|mp4|mov|m4v|mp3|wav|aac|m4a)$/i.test(a.path)) fail('UNSUPPORTED_ASSET_EXTENSION');
    assetMap.set(a.asset_id,a);
  }
  let previous = 0;
  const seen = new Set();
  for (const scene of edl.scenes ?? []) {
    if (seen.has(scene.scene_id) || !int(scene.from_frame) || !int(scene.duration_frames) || scene.from_frame !== previous || scene.duration_frames <= 0) fail('EDL_PARTITION_INVALID');
    seen.add(scene.scene_id);
    previous += scene.duration_frames;
    if (!['a_roll','split_screen','demo','motion_graphic'].includes(scene.layout) || !scene.layers?.length) fail('UNSUPPORTED_LAYOUT');
    if (!( (scene.split_ratio ?? .58) >= .2 && (scene.split_ratio ?? .58) <= .8)) fail('SPLIT_RATIO_OUTSIDE_RANGE');
    for (const layer of scene.layers) {
      if (!['video','image','text','graphic','placeholder'].includes(layer.kind)) fail('UNSUPPORTED_LAYER');
      if (!['full','top','bottom','left','right','pip'].includes(layer.panel ?? 'full')) fail('UNSUPPORTED_PANEL');
      if (['video','image'].includes(layer.kind)) {
        const asset = assetMap.get(layer.asset_id);
        if (!asset || asset.kind !== layer.kind) fail('LAYER_ASSET_UNRESOLVED');
        const trim = layer.trim_before_frames ?? 0;
        if (layer.kind === 'video' && (!int(trim) || trim < 0 || !int(asset.duration_frames) || trim + scene.duration_frames > asset.duration_frames)) fail('VIDEO_TRIM_EXCEEDS_ASSET');
      }
      if (production && layer.kind === 'placeholder') fail('SHOOT_OR_ASSET_PENDING');
      if (production && layer.kind === 'graphic') fail('UNBUILT_GRAPHIC_PLAN');
    }
  }
  if (previous !== edl.duration_frames) fail('EDL_COVERAGE_INCOMPLETE');
  if (production && edl.pending_audio_assets?.length) fail('AUDIO_RECORDING_OR_PLACEMENT_PENDING');
  for (const cap of edl.captions ?? []) if (!int(cap.from_frame) || !int(cap.duration_frames) || cap.from_frame < 0 || cap.duration_frames <= 0 || cap.from_frame + cap.duration_frames > previous || !cap.text?.trim()) fail('CAPTION_OUTSIDE_TIMELINE');
  for (const stem of edl.audio_stems ?? []) {
    const asset = assetMap.get(stem.asset_id);
    const trim = stem.trim_before_frames ?? 0;
    if (!asset || asset.kind !== 'audio' || !['speech','music','ambience','sfx'].includes(stem.role)) fail('AUDIO_ASSET_UNRESOLVED');
    if (!int(stem.from_frame) || !int(stem.duration_frames) || !int(trim) || trim < 0 || stem.from_frame < 0 || stem.duration_frames <= 0 || stem.from_frame + stem.duration_frames > previous || !int(asset.duration_frames) || trim + stem.duration_frames > asset.duration_frames) fail('AUDIO_OUTSIDE_TIMELINE');
    if (!(stem.volume >= 0 && stem.volume <= 1)) fail('AUDIO_GAIN_OUTSIDE_RANGE');
  }
  if(production) {
    if(!['REQUIRED_RECORDED_SPEECH','NO_SPEECH'].includes(edl.speech_policy)) fail('SPEECH_POLICY_REQUIRED');
    const speechIds=[...new Set((edl.audio_stems??[]).filter(s=>s.role==='speech').map(s=>s.asset_id))].sort();
    if(edl.speech_policy==='REQUIRED_RECORDED_SPEECH') {
      if(!speechIds.length) fail('RECORDED_SPEECH_STEM_REQUIRED');
      const alignment=edl.speech_alignment??{}, hashes=alignment.audio_asset_hashes??{};
      if(alignment.review_state!=='APPROVED'||!alignment.receipt_id||!edl.source_card_hash||alignment.source_card_hash!==edl.source_card_hash||Object.keys(hashes).length!==speechIds.length||speechIds.some(id=>hashes[id]!==assetMap.get(id).sha256)||alignment.alignment_plan_sha256!==alignmentPlanHash(edl)) fail('RECORDED_SPEECH_ALIGNMENT_REQUIRED');
    }
  }
  return edl;
}
