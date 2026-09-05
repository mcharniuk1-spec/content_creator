import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {validateEDL} from './contract.mjs';

const args = process.argv.slice(2);
const get = name => args[args.indexOf(name) + 1];
for (const required of ['--edl','--assets','--output','--browser']) if (!args.includes(required) || !get(required) || get(required).startsWith('--')) throw new Error(`Missing ${required}`);
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const edl = validateEDL(JSON.parse(await fs.readFile(get('--edl'),'utf8')), {production: args.includes('--production')});
if (edl.render_mode === 'PRODUCTION' && !args.includes('--production')) throw new Error('PRODUCTION_FLAG_REQUIRED');
const browserExecutable = path.resolve(get('--browser'));
await fs.access(browserExecutable);
const assetRoot = await fs.realpath(get('--assets'));
const output = path.resolve(get('--output'));
try {await fs.access(output); throw new Error('OUTPUT_EXISTS');} catch (err) {if (err.code !== 'ENOENT') throw err;}
await fs.mkdir(path.dirname(output),{recursive:true});
const scratch = await fs.mkdtemp(path.join(os.tmpdir(),'m2-render-'));
try {
  const publicDir = path.join(scratch,'public');
  await fs.mkdir(publicDir);
  const copied = new Set();
  for (const asset of edl.assets) {
    const source = await fs.realpath(path.join(assetRoot,asset.path));
    if (!source.startsWith(assetRoot + path.sep)) throw new Error('PATH_OUTSIDE_ALLOWLIST');
    const bytes = await fs.readFile(source);
    if (sha(bytes) !== asset.sha256) throw new Error('ASSET_HASH_MISMATCH');
    if (copied.has(asset.path)) continue;
    const target = path.join(publicDir,asset.path);
    await fs.mkdir(path.dirname(target),{recursive:true});
    await fs.writeFile(target,bytes,{flag:'wx'});
    copied.add(asset.path);
  }
  const entryPoint = path.join(path.dirname(fileURLToPath(import.meta.url)),'src','index.tsx');
  const serveUrl = await bundle({entryPoint, publicDir, outDir:path.join(scratch,'bundle')});
  const inputProps = {edl};
  const composition = await selectComposition({serveUrl,id:'M2Studio',inputProps,browserExecutable});
  await renderMedia({serveUrl,composition,inputProps,codec:'h264',outputLocation:output,browserExecutable,concurrency:2,crf:22});
  const receipt = {schema:'m2.remotion-render-receipt.v1',status:'RENDERED_REVIEW_REQUIRED',render_mode:edl.render_mode,remotion_version:'4.0.520',edl_sha256:sha(await fs.readFile(get('--edl'))),output_sha256:sha(await fs.readFile(output)),duration_frames:edl.duration_frames,fps:edl.fps,assets:edl.assets.map(a=>({asset_id:a.asset_id,sha256:a.sha256})),provider_execution:false,downloaded_browser:false};
  await fs.writeFile(output+'.receipt.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  process.stdout.write(JSON.stringify(receipt)+'\n');
} finally {
  await fs.rm(scratch,{recursive:true,force:true});
}
