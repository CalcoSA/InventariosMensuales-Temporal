/* Independent browser-storage sessions for draft load tests, without network access. */
const fs=require("fs"),vm=require("vm"),{performance}=require("perf_hooks");
const script=fs.readFileSync(require("path").join(__dirname,"../app/static/js/monthly.js"),"utf8");
const users=Number(process.argv[2]);
let calls=0;
const start=performance.now();
const tasks=Array.from({length:users},(_,index)=>Promise.resolve().then(()=>{
  const storage=new Map(),timers=new Map();
  const context=vm.createContext({
    document:{addEventListener(){},getElementById:()=>({value:""})},
    window:{addEventListener(){}},
    localStorage:{setItem:(k,v)=>storage.set(k,v),getItem:k=>storage.get(k)??null,removeItem:k=>storage.delete(k)},
    setTimeout:(fn,delay)=>{if(delay!==500)throw new Error("debounce");timers.set(1,fn);return 1;},
    clearTimeout:id=>timers.delete(id),
    monthlyApi:new Proxy({},{get:()=>{calls++;throw new Error("draft contacted Google");}}),console
  });
  vm.runInContext(script,context);
  vm.runInContext(
    "puntoVentaActual='PDV "+index+"';fechaActual='2026-09-18';categoriaActual='Bebidas';"+
    "productos=[{item:'000123',cerrado:'4',abierto:'2.5'}];guardarBorrador();",context);
  if(storage.size!==0||timers.size!==1)throw new Error("debounce not preserved");
  [...timers.values()][0]();
  vm.runInContext("productos=[{item:'000123',cerrado:'',abierto:''}];recuperarBorrador();"+
                  "if(productos[0].cerrado!=='4'||productos[0].abierto!=='2.5')throw new Error('restore');",context);
  if(storage.size!==1)throw new Error("storage");
  return true;
}));
Promise.all(tasks).then(results=>process.stdout.write(JSON.stringify({
  usuarios:users,flujo:"drafts",exitos:results.length,duplicadosRechazados:0,fallos:0,
  segundos:(performance.now()-start)/1000,maxEspera:0,llamadasGoogle:calls,
  lecturasSheets:0,escriturasSheets:0,singleFlightEsperas:0,respuestas429:0
}))).catch(error=>{console.error(error.message);process.exitCode=1;});
