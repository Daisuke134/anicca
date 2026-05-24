#!/usr/bin/env bash
# camofox helper lib for anicca-monk-factory. Source it.
#   source ~/.openclaw/skills/anicca-monk-factory-v3/scripts/lib/camo.sh
# Deterministic REST calls to the camofox daemon (:9377). LLM judgment stays in SKILL.md.
CF_HOST="${CF_HOST:-http://localhost:9377}"
CF_USER="${CF_USER:-anicca}"
CF_SESSION="${CF_SESSION:-default}"

camo_up() { bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh >/dev/null 2>&1; }

camo_open() { # url -> tabId
  curl -sS -X POST "$CF_HOST/tabs" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg url "$1" --arg u "$CF_USER" --arg s "$CF_SESSION" '{url:$url,userId:$u,sessionKey:$s}')" | jq -r .tabId
}
camo_nav()  { curl -sS -X POST "$CF_HOST/tabs/$1/navigate" -H 'Content-Type: application/json' -d "$(jq -n --arg url "$2" --arg u "$CF_USER" --arg s "$CF_SESSION" '{url:$url,userId:$u,sessionKey:$s}')" >/dev/null; }
camo_url()  { curl -sS "$CF_HOST/tabs/$1/snapshot?userId=$CF_USER&sessionKey=$CF_SESSION" | jq -r .url; }
camo_text() { curl -sS "$CF_HOST/tabs/$1/snapshot?userId=$CF_USER&sessionKey=$CF_SESSION" | jq -r .snapshot; }
camo_shot() { curl -sS "$CF_HOST/tabs/$1/screenshot?userId=$CF_USER&sessionKey=$CF_SESSION" -o "$2"; }

camo_click_ref() { curl -sS -X POST "$CF_HOST/tabs/$1/click" -H 'Content-Type: application/json' -d "$(jq -n --arg ref "$2" --arg u "$CF_USER" --arg s "$CF_SESSION" '{ref:$ref,userId:$u,sessionKey:$s}')"; }
# REAL-MOUSE click by CSS/Playwright selector (boundingBox center). Use for React chips + buttons that must blur fields.
camo_click_sel() { curl -sS -X POST "$CF_HOST/tabs/$1/click" -H 'Content-Type: application/json' -d "$(jq -n --arg sel "$2" --arg u "$CF_USER" --arg s "$CF_SESSION" '{selector:$sel,userId:$u,sessionKey:$s}')"; }
camo_press() { curl -sS -X POST "$CF_HOST/tabs/$1/press" -H 'Content-Type: application/json' -d "$(jq -n --arg k "$2" --arg u "$CF_USER" --arg s "$CF_SESSION" '{key:$k,userId:$u,sessionKey:$s}')" >/dev/null; }
camo_type_sel() { curl -sS -X POST "$CF_HOST/tabs/$1/type" -H 'Content-Type: application/json' -d "$(jq -n --arg sel "$2" --arg t "$3" --arg u "$CF_USER" --arg s "$CF_SESSION" '{selector:$sel,text:$t,userId:$u,sessionKey:$s,mode:"keyboard"}')"; }
camo_upload() { curl -sS -X POST "$CF_HOST/tabs/$1/upload" -H 'Content-Type: application/json' -d "$(jq -n --arg f "$2" --arg sel "${3:-input[type=file]}" --arg u "$CF_USER" --arg s "$CF_SESSION" '{files:[$f],selector:$sel,userId:$u,sessionKey:$s}')"; }
# eval arbitrary JS (returns .result). $2 = JS expression string.
camo_eval() { curl -sS -X POST "$CF_HOST/tabs/$1/evaluate" -H 'Content-Type: application/json' -d "$(jq -n --arg e "$2" --arg u "$CF_USER" --arg s "$CF_SESSION" '{expression:$e,userId:$u,sessionKey:$s}')"; }
# JS .click() the first <button> whose exact text matches $2 (regex-escaped literal). For modal buttons camofox locator times out on.
camo_jsclick_btn() { camo_eval "$1" "(()=>{const b=[...document.querySelectorAll('button')].find(x=>new RegExp('^'+$(jq -Rn --arg t "$2" '$t')+'\$','i').test((x.innerText||'').trim()));if(b){b.click();return{clicked:true}}return{clicked:false}})()"; }
