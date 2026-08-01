"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const MANIFEST_PATH = path.join(__dirname, "../config/yc-application-provider.json");
const MAIN_FIELDS = Object.freeze(["name","describe","url","productLink","make","where","wherewhy","howfar","worked","techstack","since","acc","exp","get","money","ideas","whyapply","howhear","cofounder","others2"]);
const PAGE_FIELDS = Object.freeze({main:MAIN_FIELDS,video:Object.freeze(["founder_video"]),demo:Object.freeze(["demo_video"]),progress:Object.freeze(["usernums","revenuesource","growthrate","monthly_revenue","people_using_yes","have_revenue_yes"])});
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,SHA=/^[0-9a-f]{64}$/;
const MAIN_TEXT=new Set(["name","describe","url","productLink","where"]);
const QUESTIONS=Object.freeze({people_using_yes:"Are people using your product?",have_revenue_yes:"Do you have revenue?"});
const READBACK=Object.freeze({main:"exact_value_after_save",video:"remote_media_ready_and_remove_control",demo:"remote_media_ready_and_remove_control",progress:"exact_value_and_selected_option_after_save"});
function fail(reason){throw new Error(`YC application provider ${reason} invalid`);}
function stable(value){if(Array.isArray(value))return`[${value.map(stable).join(",")}]`;if(value&&typeof value==="object")return`{${Object.keys(value).sort().map(key=>`${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;return JSON.stringify(value);}
function digest(value){return createHash("sha256").update(stable(value),"utf8").digest("hex");}
function exactKeys(value,keys,label){if(!value||typeof value!=="object"||Array.isArray(value)||stable(Object.keys(value).sort())!==stable([...keys].sort()))fail(label);}
function deepFreeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const nested of Object.values(value))deepFreeze(nested);}return value;}
function exactLocator(field,page){
 const locator=field.locator;
 if(field.kind==="choice"){
  exactKeys(locator,["strategy","question_text","option_text","cardinality"],"choice locator");
  if(locator.strategy!=="question_scoped_option"||locator.question_text!==QUESTIONS[field.name]||locator.option_text!=="Yes"||locator.cardinality!==1)fail("choice locator");
  return;
 }
 exactKeys(locator,["strategy","selector","cardinality"],"CSS locator");
 const selector=field.kind==="file"?"input[type=file][accept*=video]":field.kind==="indexed_inputs"?'input[placeholder="USD$"]':`[name=${field.name}]`,cardinality=field.kind==="indexed_inputs"?6:1;
 if(locator.strategy!=="css_exact"||locator.selector!==selector||locator.cardinality!==cardinality)fail("CSS locator");
 if(page==="main"&&field.kind!==(MAIN_TEXT.has(field.name)?"text":"textarea"))fail("main field kind");
}
function exactSaveAndReadback(page){
 exactKeys(page.readback,["required","strategy"],"readback schema");
 if(page.readback.required!==true||page.readback.strategy!==READBACK[page.name])fail("readback contract");
 if(["main","progress"].includes(page.name)){
  exactKeys(page.save,["kind","text","count"],"save schema");
  if(page.save.kind!=="button_exact_text"||page.save.text!=="Save changes"||page.save.count!==1)fail("save contract");
 }else{
  exactKeys(page.save,["kind","count"],"save schema");
  if(page.save.kind!=="upload_completion"||page.save.count!==1)fail("save contract");
 }
}
function validateManifest(manifest){
 exactKeys(manifest,["schema_version","provider_id","successor_provider","ported_from","browser_route_id","mode","submit_operations","pages"],"manifest schema");
 if(manifest.schema_version!==1||manifest.provider_id!=="yc-application"||manifest.successor_provider!=="apply-to-funder"||manifest.ported_from!=="apply-to-yc"||manifest.browser_route_id!=="yc-application"||manifest.mode!=="preview_only"||manifest.submit_operations!==0||!Array.isArray(manifest.pages)||stable(manifest.pages.map(({name})=>name))!==stable(Object.keys(PAGE_FIELDS)))fail("manifest identity");
 if(/selector_filter|literal:click|9223|submit application/i.test(JSON.stringify(manifest)))fail("unsafe legacy pattern");
 for(const page of manifest.pages){
  exactKeys(page,["name","path_template","atomic","navigate_count","save","fields","readback"],"page schema");
  const expected=PAGE_FIELDS[page.name],suffix=page.name==="main"?"":`/${page.name}`;
  if(!expected||page.path_template!==`/apps/{draft_id}/edit${suffix}`||page.atomic!==true||page.navigate_count!==1||!Array.isArray(page.fields)||stable(page.fields.map(({name})=>name))!==stable(expected))fail("page contract");
  exactSaveAndReadback(page);
  for(const field of page.fields){
   const expectedKind=page.name==="main"?(MAIN_TEXT.has(field.name)?"text":"textarea"):page.name==="progress"?({usernums:"textarea",revenuesource:"textarea",growthrate:"textarea",monthly_revenue:"indexed_inputs",people_using_yes:"choice",have_revenue_yes:"choice"})[field.name]:"file";
   if(field.kind!==expectedKind)fail("field kind");
   exactKeys(field,field.kind==="indexed_inputs"?["name","kind","count","locator","setter"]:field.kind==="choice"||field.kind==="file"?["name","kind","locator"]:["name","kind","locator","setter"],"field schema");
   exactLocator(field,page.name);
   if(["text","textarea","indexed_inputs"].includes(field.kind)){exactKeys(field.setter,["strategy","events"],"setter schema");if(field.setter.strategy!=="native_value_setter"||stable(field.setter.events)!==stable(["input","change","blur"]))fail("React setter");}
   if(field.kind==="indexed_inputs"&&field.count!==6)fail("monthly revenue");
  }
 }
 const choices=manifest.pages.find(({name})=>name==="progress").fields.filter(({kind})=>kind==="choice");if(new Set(choices.map(({locator})=>locator.question_text)).size!==2)fail("choice identity");return manifest;
}
function loadYcApplicationProviderManifest(options={}){let manifest;try{manifest=JSON.parse((options.readFile||fs.readFileSync)(options.path||MANIFEST_PATH,"utf8"));}catch{fail("manifest file");}validateManifest(manifest);return deepFreeze(manifest);}
function currentSource(ref){return /^(?:application-kit:\/(?:\/KIT\.md|\/answers\/q(?:0[1-9]|10)_[a-z0-9_]+\.(?:en|ja)\.md)(?:#[A-Za-z0-9._-]+)?|(?:dashboard-snapshot|founder-profile|provider-surface):\/\/current#[^\s]+)$/.test(ref);}
function validateResolved(field,entry){
 exactKeys(entry,field.kind==="file"?["source_ref","artifact_digest"]:["value","source_ref","source_digest"],"resolved field");
 if(field.kind==="file"){if(!SHA.test(String(entry.artifact_digest||""))||!/^application-kit:\/\/videos\/[A-Za-z0-9._-]+\.mp4$/.test(String(entry.source_ref||"")))fail("file source");if(field.name==="founder_video"&&entry.source_ref!=="application-kit://videos/Anicca_intro_EN.mp4")fail("founder video source");}
 else if(!currentSource(String(entry.source_ref||""))||!SHA.test(String(entry.source_digest||"")))fail("source reference");
 else if(field.kind==="indexed_inputs"){if(!Array.isArray(entry.value)||entry.value.length!==6||entry.value.some(value=>typeof value!=="number"||!Number.isFinite(value)||value<0))fail("monthly revenue values");}
 else if(field.kind==="choice"){if(entry.value!==true)fail("choice value");}
 else if(typeof entry.value!=="string"||!entry.value.trim()||entry.value.length>100000)fail("text value");
}
function buildYcApplicationProviderPlan(input={},options={}){
 const draftId=String(input.draftId||"").toLowerCase(),manifest=options.manifest?validateManifest(structuredClone(options.manifest)):loadYcApplicationProviderManifest(options),resolved=input.resolved;
 if(!UUID.test(draftId)||!resolved||typeof resolved!=="object"||Array.isArray(resolved))fail("input");const expectedKeys=manifest.pages.flatMap(page=>page.fields.map(field=>`${page.name}.${field.name}`));if(stable(Object.keys(resolved).sort())!==stable([...expectedKeys].sort()))fail("resolved inventory");
 const operations=manifest.pages.map(page=>{const mutations=page.fields.map(field=>{const entry=resolved[`${page.name}.${field.name}`];validateResolved(field,entry);const mutation=field.kind==="file"?{field:field.name,kind:field.kind,locator:structuredClone(field.locator),source_ref:entry.source_ref,artifact_digest:entry.artifact_digest}:{field:field.name,kind:field.kind,locator:structuredClone(field.locator),setter:field.setter?structuredClone(field.setter):undefined,value:structuredClone(entry.value),source_ref:entry.source_ref,source_digest:entry.source_digest};return Object.fromEntries(Object.entries(mutation).filter(([,value])=>value!==undefined));});return{page:page.name,url_path:page.path_template.replace("{draft_id}",draftId),atomic:true,navigate_count:1,mutations,save:structuredClone(page.save),readback:{...structuredClone(page.readback),fields:page.fields.map(({name})=>name)}};});
 const core={schema_version:1,provider_id:manifest.provider_id,browser_route_id:manifest.browser_route_id,mode:"preview_only",draft_id:draftId,manifest_digest:digest(manifest),logical_field_count:expectedKeys.length,submit_operations:0,operations};return deepFreeze({...core,plan_digest:digest(core)});
}
module.exports={MAIN_FIELDS,buildYcApplicationProviderPlan,loadYcApplicationProviderManifest};
