// Credential-isolated dispatch gateway. CPU/media work stays on the worker host.
export default {
  async fetch(request, env) {
    if (!env.GATEWAY_TOKEN || !env.WORKER_ORIGIN || !env.WORKER_TOKEN) {
      return new Response('Not configured', {status:503});
    }
    if (request.headers.get('Authorization') !== `Bearer ${env.GATEWAY_TOKEN}`) {
      return new Response('Unauthorized', {status:401});
    }
    const url = new URL(request.url);
    if (request.method !== 'POST' || url.pathname !== '/v1/jobs') {
      return new Response('Not found', {status:404});
    }
    if (!request.headers.get('Content-Type')?.startsWith('application/json')) {
      return new Response('JSON required', {status:415});
    }
    const reader=request.body?.getReader();
    if (!reader) return new Response('Body required',{status:400});
    const chunks=[]; let size=0;
    for (;;) {
      const {value,done}=await reader.read(); if(done) break;
      size+=value.length;
      if(size>16384) {await reader.cancel();return new Response('Too large',{status:413});}
      chunks.push(value);
    }
    const bytes=new Uint8Array(size); let offset=0;
    for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
    let job;
    try{job=JSON.parse(new TextDecoder().decode(bytes));}catch{return new Response('Invalid JSON',{status:400});}
    if (!job || !['asr','frames','reconcile','render_fixture'].includes(job.stage)
      || !/^[0-9a-f]{64}$/.test(job.input_sha256 || '')
      || Object.keys(job).some(k=>!['stage','input_sha256','release_id'].includes(k))
      || !/^[a-z0-9_-]{1,80}$/.test(job.release_id||'')) {
      return new Response('Invalid job',{status:400});
    }
    let target;
    try {target=new URL('/v1/jobs',env.WORKER_ORIGIN);if(target.protocol!=='https:') throw Error();}
    catch{return new Response('Not configured',{status:503});}
    try {
      const response=await fetch(target,{method:'POST',headers:{'Authorization':`Bearer ${env.WORKER_TOKEN}`,
        'Content-Type':'application/json','Idempotency-Key':`${job.stage}:${job.input_sha256}`},
        body:JSON.stringify(job),redirect:'error',signal:AbortSignal.timeout(10000)});
      // Never echo upstream secrets, exception details or payloads.
      return new Response(JSON.stringify({state:response.ok?'submitted':'upstream_failed'}),
        {status:response.ok?202:502,headers:{'Content-Type':'application/json'}});
    } catch{return new Response('Outcome unknown; reconcile by input hash',{status:504});}
  }
};
