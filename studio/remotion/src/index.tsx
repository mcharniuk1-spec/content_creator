import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {StudioComposition} from './Composition';
import type {EDL} from './types';

const empty: EDL = {schema: 'm2.remotion-edl.v1', card_id: 'preview', title: 'Preview', fps: 30, width: 1080, height: 1920, duration_frames: 30, scenes: [{scene_id: 'intro', from_frame: 0, duration_frames: 30, layout: 'motion_graphic', layers: [{kind: 'graphic', text: 'M2 LAB'}]}], assets: [], captions: [], audio_stems: [], render_mode: 'PREVIS', review_state: 'REVIEW_PENDING'};
const Root = () => <Composition id="M2Studio" component={StudioComposition} durationInFrames={30} fps={30} width={1080} height={1920} defaultProps={{edl: empty}} calculateMetadata={({props}) => ({durationInFrames: props.edl.duration_frames, fps: props.edl.fps, width: props.edl.width, height: props.edl.height})}/>;
registerRoot(Root);
