"use strict";
const {createHash}=require("node:crypto");
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EXPECTED_EDUCATION=[
  {institution:"Nara Institute of Science and Technology",degree:"MS",field:"Information Science",from:"2024-04",to:"2027-03"},
  {institution:"Keio University",degree:"BA",field:"Politics",from:"2020-04",to:"2024-03"},
];
function stable(v){if(Array.isArray(v))return`[${v.map(stable).join(",")}]`;if(v&&typeof v==="object")return`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${stable(v[k])}`).join(",")}}`;return JSON.stringify(v)}
function buildYcFounderProfilePatch(input={}){
  const exactEducation=JSON.stringify(input.education)===JSON.stringify(EXPECTED_EDUCATION);
  if(!UUID.test(String(input.draftId||""))||!UUID.test(String(input.bioId||""))
    ||!/^[0-9a-f]{64}$/.test(String(input.profileDigest||""))||!/^[0-9a-f]{64}$/.test(String(input.kitDigest||""))
    ||input.dateOfBirth!=="2002-01-30"||input.city!=="Tokyo Japan"||input.role!=="Founder"||/MUFG/i.test(input.role)
    ||input.equityPercent!==100||input.technicalFounder!==true||input.currentlyInSchool!==true
    ||input.commitExclusiveIfAccepted!==true||input.commitmentSource!=="execution-spec://O1C-07+application-kit://KIT.md#where"
    ||!exactEducation||input.duplicateEducationDeletes!==4)throw new Error("YC founder profile patch invalid");
  const core={schema_version:1,draft_id:input.draftId.toLowerCase(),bio_id:input.bioId.toLowerCase(),
    profile_digest:input.profileDigest,kit_digest:input.kitDigest,date_of_birth:input.dateOfBirth,city:input.city,
    role:input.role,equity_percent:100,technical_founder:true,currently_in_school:true,commit_exclusive_if_accepted:true,
    commitment_source:input.commitmentSource,education:EXPECTED_EDUCATION,duplicate_education_deletes:4,
    save_and_return_clicks:1,submit_clicks:0};
  return Object.freeze({...core,patch_digest:createHash("sha256").update(stable(core)).digest("hex")});
}
module.exports={buildYcFounderProfilePatch};
