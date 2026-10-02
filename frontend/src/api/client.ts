export type ApiOptions=RequestInit & {apiKey?:string};
const base=import.meta.env.VITE_API_BASE_URL||'';
export async function api<T=any>(path:string,options:ApiOptions={},fallbackKey=''):Promise<T>{const headers=new Headers(options.headers);const key=options.apiKey||fallbackKey;if(key)headers.set('X-API-Key',key);const r=await fetch(`${base}${path}`,{...options,headers});const body=await r.json().catch(()=>({}));if(!r.ok)throw new Error(body?.error?.message||body?.detail||`HTTP ${r.status}`);return body as T}
