// One deterministic still per authored shot; source evidence is never implied.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {validateEDL} from './contract.mjs';

const args=process.argv.slice(2), get=name=>args[args.indexOf(name)+1];
for(const key of ['--edls','--output','--browser']) if(!args.includes(key)||!get(key)||get(key).startsWith('--')) throw new Error(`Missing ${key}`);
const root=path.resolve(get('--edls')), output=path.resolve(get('--output')), browserExecutable=path.resolve(get('--browser'));
await fs.access(browserExecutable); await fs.mkdir(output,{recursive:true});
const scratch=await fs.mkdtemp(path.join(os.tmpdir(),'m2-storyboards-'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
let browser;
try {
  const publicDir=path.join(scratch,'public');await fs.mkdir(publicDir);
  const serveUrl=await bundle({entryPoint:path.join(path.dirname(fileURLToPath(import.meta.url)),'src/index.tsx'),publicDir,outDir:path.join(scratch,'bundle')});
  browser=await openBrowser('chrome',{browserExecutable});
  const receipts=[];
  for(const file of (await fs.readdir(root)).filter(f=>f.endsWith('.edl.json')).sort()) {
    const bytes=await fs.readFile(path.join(root,file));
    const edl=validateEDL(JSON.parse(bytes));
    if(edl.assets.length||edl.render_mode!=='PREVIS') throw new Error('STORYBOARD_ONLY_UNBOUND_PREVIS');
    if(!/^[A-Za-z0-9_-]+$/.test(edl.card_id)) throw new Error('INVALID_CARD_ID');
    const cardRoot=path.join(output,edl.card_id);await fs.mkdir(cardRoot);
    const inputProps={edl};
    const composition=await selectComposition({serveUrl,id:'M2Studio',inputProps,browserExecutable,puppeteerInstance:browser});
    const frames=[];
    for(let i=0;i<edl.scenes.length;i++) {
      const scene=edl.scenes[i], frame=scene.from_frame+Math.floor(scene.duration_frames/2);
      const filename=`shot-${String(i+1).padStart(2,'0')}.png`, target=path.join(cardRoot,filename);
      await renderStill({serveUrl,composition,inputProps,frame,output:target,imageFormat:'png',scale:.5,browserExecutable,puppeteerInstance:browser});
      frames.push({scene_id:scene.scene_id,frame,start_frame:scene.from_frame,end_frame:scene.from_frame+scene.duration_frames,path:filename,sha256:sha(await fs.readFile(target))});
    }
    const receipt={schema:'m2.remotion-storyboard.v1',card_id:edl.card_id,edl_sha256:sha(bytes),fps:edl.fps,duration_frames:edl.duration_frames,frames,source_evidence:false,provider_execution:false,review_state:'REVIEW_PENDING',render_mode:'PREVIS'};
    await fs.writeFile(path.join(cardRoot,'receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
    receipts.push({card_id:edl.card_id,frame_count:frames.length,receipt_sha256:sha(await fs.readFile(path.join(cardRoot,'receipt.json')))});
  }
  await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify({schema:'m2.storyboard-slate.v1',remotion_version:'4.0.520',cards:receipts,provider_execution:false},null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify({cards:receipts.length,frames:receipts.reduce((n,r)=>n+r.frame_count,0),status:'RENDERED_REVIEW_REQUIRED'})+'\n');
} finally {
  if(browser) await browser.close({silent:true});
  await fs.rm(scratch,{recursive:true,force:true});
}
