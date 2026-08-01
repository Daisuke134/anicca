"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { buildYcFounderProfilePatch } = require("./yc-founder-profile.js");

function valid() { return {
  draftId: "0b61fe42-e383-490d-b60e-04f1ad7ec5df", bioId: "721f696b-0566-4a16-bda7-a9c368b1eac1",
  profileDigest: "a".repeat(64), kitDigest: "b".repeat(64),
  dateOfBirth: "2002-01-30", city: "Tokyo Japan", role: "Founder", equityPercent: 100,
  technicalFounder: true, currentlyInSchool: true, commitExclusiveIfAccepted: true,
  commitmentSource: "execution-spec://O1C-07+application-kit://KIT.md#where",
  education: [
    { institution: "Nara Institute of Science and Technology", degree: "MS", field: "Information Science", from: "2024-04", to: "2027-03" },
    { institution: "Keio University", degree: "BA", field: "Politics", from: "2020-04", to: "2024-03" },
  ], duplicateEducationDeletes: 4,
}; }

test("canonical founder facts create an exact non-submit completion patch", () => {
  const patch=buildYcFounderProfilePatch(valid());
  assert.equal(patch.education.length,2); assert.equal(patch.equity_percent,100);
  assert.equal(patch.commit_exclusive_if_accepted,true); assert.equal(patch.duplicate_education_deletes,4);
  assert.equal(patch.save_and_return_clicks,1); assert.equal(patch.submit_clicks,0);
  assert.match(patch.patch_digest,/^[0-9a-f]{64}$/);
});

test("old graduation, wrong employer language, incomplete education, unsafe equity, and missing intent source fail closed", () => {
  const bad=[
    {education:[{...valid().education[0],to:"2026-03"},valid().education[1]]},
    {role:"MUFG CEO"}, {education:valid().education.slice(0,1)}, {equityPercent:99},
    {commitmentSource:""}, {profileDigest:"bad"},
  ];
  for(const x of bad) assert.throws(()=>buildYcFounderProfilePatch({...valid(),...x}),/founder profile/i);
});
