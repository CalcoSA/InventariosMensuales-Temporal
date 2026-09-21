/* Differential oracle. Executes unchanged supplied .gs in an isolated VM; no network. */
const fs = require("fs"), path = require("path"), vm = require("vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
function range(values, r=1, c=1, rows=values.length, cols=Math.max(0,...values.map(v=>v.length))) {
  return {getDisplayValues:()=>Array.from({length:rows},(_,i)=>Array.from({length:cols},(_,j)=>values[r-1+i]?.[c-1+j]??"")),
          getValues:()=>range(values,r,c,rows,cols).getDisplayValues()};
}
function sheet(data) {
  const values = data.display || data.values || [];
  return {
    getName:()=>data.name || "Mensual", getLastRow:()=>values.length,
    getLastColumn:()=>Math.max(0,...values.map(v=>v.length)),
    getRange:(...args)=>range(values,...args),
    getDataRange:()=>({...range(values),getMergedRanges:()=> (data.merged||[]).map(a=>({
      getDisplayValue:()=>a.texto, getRow:()=>a.fila, getColumn:()=>a.columnaInicio, getLastColumn:()=>a.columnaFin
    }))})
  };
}
function execute(test) {
  const sandbox = {
    console:{log(){},error(){}},
    CacheService:{getScriptCache:()=>({get:()=>null,put(){},remove(){}})},
    Session:{getScriptTimeZone:()=>"America/Bogota"},
    Utilities:{
      newBlob:content=>({getBytes:()=>Buffer.from(content,"utf8")}),
      base64Encode:bytes=>Buffer.from(bytes).toString("base64"),
      formatDate:(date,_zone,_format)=>new Intl.DateTimeFormat("en-CA",{timeZone:"America/Bogota",year:"numeric",month:"2-digit",day:"2-digit"}).format(date)
    }
  };
  const context = vm.createContext(sandbox);
  const filename = test.project === "generator" ? "generador_inventario_mensual.gs" : "inventarios_mensuales_pdv.gs";
  vm.runInContext(fs.readFileSync(path.join(__dirname,"../legacy",filename),"utf8"),context);
  let args = test.args || [];
  const fn = test.function;
  if (test.book) {
    const sheets = test.book.map(sheet);
    const book = {getSheets:()=>sheets,getSheetByName:name=>sheets.find(s=>s.getName()===name)||null};
    sandbox.SpreadsheetApp = {openById:()=>book};
    sandbox.obtenerLibroMensualPDV_ = ()=>book;
  }
  sandbox.crearClaveCacheMensual_ = ()=>"cache";
  sandbox.validarAccesoAdministrador_ = ()=>{};
  if (fn === "detectarColumnas_") args = [sheet({display:args[0]})];
  if (["esCategoriaCandidata_","categoriaEnMismaFila_"].includes(fn)) {
    const index = fn==="esCategoriaCandidata_" ? 1 : 2;
    args[index] = new Map(args[index].map(x=>[x,{}]));
  }
  if (fn === "detectarAnclasCategorias_") {
    const [values, products, merged] = args;
    args = [sheet({display:values, merged}), values, new Map(products.map(x=>[x,{}]))];
  }
  if (fn === "obtenerCategoriasPorCodigo_") args[1] = new Map(Object.entries(args[1]));
  if (fn === "construirFilasSalida_") args = [new Map(Object.entries(args[0])),new Map(Object.entries(args[1]).map(([k,v])=>[k,new Set(v)]))];
  if (test.csvFiles) {
    const files=test.csvFiles.map(data=>({
      getMimeType:()=>"application/vnd.google-apps.spreadsheet", getName:()=>data.name, getId:()=>data.id
    }));
    sandbox.obtenerCarpetaBasesMensuales_=()=>({getFiles:()=>{let i=0;return {hasNext:()=>i<files.length,next:()=>files[i++]};}});
  }
  try {
    const result = sandbox[fn](...args);
    function serialize(value) {
      if (value instanceof Map) return Object.fromEntries([...value].map(([k,v])=>[k,serialize(v)]));
      if (value instanceof Set) return [...value];
      // Maps created inside VM have different prototypes.
      if (Object.prototype.toString.call(value)==="[object Map]") return Object.fromEntries([...value].map(([k,v])=>[k,serialize(v)]));
      if (Object.prototype.toString.call(value)==="[object Set]") return [...value];
      return value;
    }
    return {result:serialize(result)};
  } catch (error) { return {error:error.message}; }
}
process.stdout.write(JSON.stringify(input.map(execute)));
