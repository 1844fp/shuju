import type { NextConfig } from 'next';
const base=process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const config: NextConfig = { async rewrites(){return [{source:'/login',destination:`${base}/login`},{source:'/api/v1/:path*',destination:`${base}/api/v1/:path*`},{source:'/operations',destination:`${base}/operations`},{source:'/static/:path*',destination:`${base}/static/:path*`}];}};
export default config;
