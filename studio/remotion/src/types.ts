export type Asset = {
  asset_id: string;
  kind: 'video' | 'image' | 'audio';
  path: string;
  sha256: string;
  rights_approved: boolean;
  rights_receipt_id: string;
  duration_frames?: number;
};
export type Layer = {
  kind: 'video' | 'image' | 'text' | 'graphic' | 'placeholder';
  asset_id?: string;
  text?: string;
  panel?: 'full' | 'top' | 'bottom' | 'left' | 'right' | 'pip';
  trim_before_frames?: number;
  muted?: boolean;
};
export type Scene = {scene_id: string; from_frame: number; duration_frames: number; layout: 'a_roll' | 'split_screen' | 'demo' | 'motion_graphic'; split_ratio?: number; layers: Layer[]};
export type EDL = {
  schema: 'm2.remotion-edl.v1';
  card_id: string;
  title: string;
  fps: number;
  width: number;
  height: number;
  duration_frames: number;
  scenes: Scene[];
  assets: Asset[];
  captions: {from_frame: number; duration_frames: number; text: string}[];
  audio_stems: {asset_id: string; role: 'speech' | 'music' | 'ambience' | 'sfx'; from_frame: number; duration_frames: number; trim_before_frames?: number; volume: number}[];
  pending_audio_assets?: string[];
  speech_policy?: 'REQUIRED_RECORDED_SPEECH' | 'NO_SPEECH';
  speech_alignment?: {review_state: string; receipt_id: string | null; source_card_hash?: string; audio_asset_hashes?: Record<string, string>; alignment_plan_sha256?: string};
  render_mode: 'PREVIS' | 'PRODUCTION';
  review_state: string;
};
