import crypto from "node:crypto";
import http from "node:http";
import fs from "node:fs";

const saKey = JSON.parse(fs.readFileSync("/tmp/zitadel-admin-sa.json", "utf8"));
function b64(s) { return Buffer.from(s).toString("base64url"); }
const now = Math.floor(Date.now() / 1000);
const msg = b64(JSON.stringify({alg:"RS256",kid:saKey.keyId})) + "." + b64(JSON.stringify({iss:saKey.userId,sub:saKey.userId,aud:"http://localhost:8080",iat:now,exp:now+3600}));
const sig = crypto.sign("sha256", Buffer.from(msg), saKey.key);
const assertion = msg + "." + b64(sig);

function callM(method, path, body, extraHdrs) {
  return new Promise((resolve) => {
    const b = body ? JSON.stringify(body) : "";
    const opts = {hostname:"zitadel",port:8080,path,method,headers:{Host:"localhost:8080","Content-Type":"application/json","Content-Length":Buffer.byteLength(b)}};
    if (extraHdrs) Object.assign(opts.headers, extraHdrs);
    const req=http.request(opts,(res)=>{let d="";res.on("data",c=>d+=c);res.on("end",()=>resolve({status:res.statusCode,body:d}))});
    req.on("error",(e)=>resolve({status:0,body:e.message}));if(b)req.write(b);req.end();
  });
}

async function main() {
  const form="grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion="+encodeURIComponent(assertion)+"&scope=openid%20profile%20urn:zitadel:iam:org:project:id:zitadel:aud";
  const tr=await new Promise((resolve)=>{
    const opts={hostname:"zitadel",port:8080,path:"/oauth/v2/token",method:"POST",headers:{Host:"localhost:8080","Content-Type":"application/x-www-form-urlencoded","Content-Length":Buffer.byteLength(form)}};
    const req=http.request(opts,(res)=>{let d="";res.on("data",c=>d+=c);res.on("end",()=>resolve(JSON.parse(d)))});
    req.on("error",()=>resolve({}));req.write(form);req.end();
  });
  const at=tr.access_token;

  // Step 1: Create empty session
  const r1 = await callM("POST", "/v2/sessions", {userId:"378680523524603911",metadata:{}}, {"Authorization":"Bearer "+at});
  const session = JSON.parse(r1.body);
  const sid = session.sessionId;
  const stoken = session.sessionToken;
  console.log("Empty session:", sid, "token:", !!stoken);

  // Step 2: Verify password via checks
  const r2 = await callM("POST", "/v2/sessions/"+sid+"/checks", {password:{password:"Password1!"}}, {"Authorization":"Bearer "+stoken});
  console.log("Password check:", r2.status, r2.body.substring(0,500));

  // Step 3: Get session
  const r3 = await callM("GET", "/v2/sessions/"+sid, null, {"Authorization":"Bearer "+stoken});
  console.log("Get session:", r3.status, r3.body.substring(0,500));
}
main();
