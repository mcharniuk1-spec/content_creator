import React from 'react';
import {AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, interpolate} from 'remotion';
import type {Asset, EDL, Layer, Scene} from './types';

const panelStyle = (panel: Layer['panel'], splitRatio = .58): React.CSSProperties => {
  const shared: React.CSSProperties = {position: 'absolute', overflow: 'hidden', borderRadius: 16};
  if (panel === 'top') return {...shared, inset: `0 0 ${(1 - splitRatio) * 100 + 1}% 0`};
  if (panel === 'bottom') return {...shared, inset: `${splitRatio * 100 + 1}% 0 0 0`};
  if (panel === 'left') return {...shared, inset: '0 51% 0 0'};
  if (panel === 'right') return {...shared, inset: '0 0 0 51%'};
  if (panel === 'pip') return {...shared, right: 20, bottom: 80, width: '32%', height: '30%', zIndex: 3};
  return {...shared, inset: 0};
};

const VisualLayer: React.FC<{layer: Layer; assets: Asset[]; splitRatio?: number}> = ({layer, assets, splitRatio}) => {
  const frame = useCurrentFrame();
  const asset = assets.find(a => a.asset_id === layer.asset_id);
  const style = panelStyle(layer.panel, splitRatio);
  const mediaStyle: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'contain'};
  if (layer.kind === 'video' && asset) return <div style={style}><OffthreadVideo src={staticFile(asset.path)} style={mediaStyle} trimBefore={layer.trim_before_frames ?? 0} muted={layer.muted ?? true}/></div>;
  if (layer.kind === 'image' && asset) return <div style={style}><Img src={staticFile(asset.path)} style={mediaStyle}/></div>;
  if (layer.kind === 'text') return <div style={{...style, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '42px 28px', zIndex: 4, pointerEvents: 'none'}}><div style={{fontSize: 48, fontWeight: 750, lineHeight: 1.12, background: '#111827ef', padding: '20px 26px', borderRadius: 18, whiteSpace: 'pre-wrap'}}>{layer.text}</div></div>;
  return <div style={{...style, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, background: layer.kind === 'placeholder' ? '#192430' : '#152d33', border: '2px solid #355364', transform: `translateY(${interpolate(frame, [0, 10], [8, 0], {extrapolateRight: 'clamp'})}px)`}}>
    <div style={{fontSize: 22, letterSpacing: 3, color: '#8bb8bb', marginBottom: 24}}>{layer.kind === 'placeholder' ? 'SHOT / ASSET PENDING' : 'DETERMINISTIC VISUAL PLAN'}</div>
    <div style={{fontSize: 36, lineHeight: 1.4, whiteSpace: 'pre-wrap'}}>{layer.text}</div>
  </div>;
};

const SceneView: React.FC<{scene: Scene; edl: EDL}> = ({scene, edl}) => <AbsoluteFill style={{padding: '200px 64px 390px'}}>
  <div style={{position: 'relative', width: '100%', height: '100%'}}>{scene.layers.map((layer, index) => <VisualLayer key={index} layer={layer} assets={edl.assets} splitRatio={scene.split_ratio}/>)}</div>
</AbsoluteFill>;

export const StudioComposition: React.FC<{edl: EDL}> = ({edl}) => <AbsoluteFill style={{background: '#0a1018', color: '#f8fafc', fontFamily: 'Arial, sans-serif'}}>
  <div style={{position: 'absolute', left: 64, top: 90, right: 96, display: 'flex', justifyContent: 'space-between', fontSize: 26, letterSpacing: 2}}><span>M2 LAB · {edl.card_id}</span><span style={{color: '#7adbbd'}}>{edl.render_mode === 'PREVIS' ? 'PREVIS · NOT FINAL' : 'REVIEW EXPORT'}</span></div>
  {edl.scenes.map(scene => <Sequence key={scene.scene_id} from={scene.from_frame} durationInFrames={scene.duration_frames}><SceneView scene={scene} edl={edl}/></Sequence>)}
  {edl.captions.map((caption, index) => <Sequence key={index} from={caption.from_frame} durationInFrames={caption.duration_frames}><div style={{position: 'absolute', bottom: 190, left: 80, right: 140, fontSize: caption.text.length > 180 ? 38 : 44, lineHeight: 1.25, fontWeight: 700, textAlign: 'center', background: '#0a1018ed', padding: 22, borderRadius: 18}}>{caption.text}</div></Sequence>)}
  {edl.audio_stems.map((stem, index) => {
    const asset = edl.assets.find(a => a.asset_id === stem.asset_id)!;
    return <Sequence key={index} from={stem.from_frame} durationInFrames={stem.duration_frames}><Audio src={staticFile(asset.path)} trimBefore={stem.trim_before_frames ?? 0} volume={stem.volume}/></Sequence>;
  })}
</AbsoluteFill>;
