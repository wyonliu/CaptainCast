(() => {
'use strict';
const $=id=>document.getElementById(id),cfg=JSON.parse($('episode-config').textContent),a=$('episode-audio'),root=$('player'),play=$('play'),seek=$('seek'),speed=$('speed'),status=$('audio-status'),timer=$('sleep'),key='captaincast-liveliva-v7-listening';
const fmt=s=>{s=Math.max(0,Math.floor(Number(s)||0));return `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;};
let saved={},lastSave=0,pendingSeek=null,dragging=false,deadline=null,stopAt=null;
try{saved=JSON.parse(localStorage.getItem(key)||'{}');}catch(e){}
const total=()=>Number.isFinite(a.duration)&&a.duration>0?a.duration:cfg.duration;
const current=()=>pendingSeek??a.currentTime??0;
const chapterAt=t=>{let i=0;cfg.chapters.forEach((c,n)=>{if(t>=c.start)i=n;});return i;};
function store(){try{localStorage.setItem(key,JSON.stringify({time:a.ended?0:current(),rate:a.playbackRate,volume:a.volume,muted:a.muted}));}catch(e){}}
function update(){const t=current(),d=total(),v=dragging?Number(seek.value):t;seek.max=d;if(!dragging)seek.value=t;$('elapsed').textContent=fmt(v);$('duration').textContent=fmt(d);seek.setAttribute('aria-valuetext',`${fmt(v)}，总时长${fmt(d)}`);$('played-clip').setAttribute('width',String(600*v/d));const ci=chapterAt(t),c=cfg.chapters[ci];$('chapter-index').textContent=c.chapter;$('chapter-title').textContent=c.title;$('chapter-read').href=`script.html?t=${Math.floor(t)}#ch-${c.chapter}`;document.querySelectorAll('[data-chapter]').forEach((b,i)=>b.setAttribute('aria-current',String(i===ci)));play.classList.toggle('playing',!a.paused);play.setAttribute('aria-label',a.paused?'播放完整对话':'暂停播放');play.setAttribute('aria-pressed',String(!a.paused));}
function clearTimer(message=''){deadline=null;stopAt=null;timer.value='off';$('timer-status').textContent=message;}
function checkTimer(){if((deadline!==null&&Date.now()>=deadline)||(stopAt!==null&&current()>=stopAt)){a.pause();clearTimer('定时已到，已为你暂停。');store();}else if(deadline!==null){const mins=Math.ceil((deadline-Date.now())/60000);$('timer-status').textContent=`将在${mins}分钟内暂停`;}}
function jump(t){const target=Math.max(0,Math.min(total(),Number(t)||0));if(a.readyState===0){pendingSeek=target;a.load();}else{pendingSeek=null;a.currentTime=target;}if(timer.value==='chapter'){const i=chapterAt(target);stopAt=cfg.chapters[i+1]?.start??total();$('timer-status').textContent='将在当前章节结束时暂停';}update();store();}
play.addEventListener('click',async()=>{if(!a.paused){a.pause();return;}checkTimer();status.textContent='正在载入音频…';try{await a.play();status.textContent='正在播放';}catch(e){status.textContent='音频暂时未能播放，请重试或下载收听。';update();}});
document.querySelectorAll('[data-skip]').forEach(b=>b.addEventListener('click',()=>jump(current()+Number(b.dataset.skip))));
$('previous').addEventListener('click',()=>{const i=chapterAt(current());jump(current()-cfg.chapters[i].start>3?cfg.chapters[i].start:cfg.chapters[Math.max(0,i-1)].start);});
$('next').addEventListener('click',()=>jump(cfg.chapters[Math.min(cfg.chapters.length-1,chapterAt(current())+1)].start));
seek.addEventListener('input',()=>{dragging=true;update();});seek.addEventListener('change',()=>{const t=Number(seek.value);dragging=false;jump(t);});
speed.addEventListener('change',()=>{a.playbackRate=Number(speed.value);a.preservesPitch=true;store();});
function volumeUI(){$('mute').setAttribute('aria-label',a.muted?'取消静音':'静音');$('mute').setAttribute('aria-pressed',String(a.muted));$('mute').style.opacity=a.muted?'.45':'1';$('volume').value=a.volume;}
$('mute').addEventListener('click',()=>{a.muted=!a.muted;volumeUI();store();});$('volume').addEventListener('input',()=>{a.volume=Number($('volume').value);a.muted=a.volume===0;volumeUI();store();});
document.querySelectorAll('[data-chapter]').forEach(b=>b.addEventListener('click',()=>{jump(cfg.chapters[Number(b.dataset.chapter)].start);status.textContent=a.paused?'已定位，点击播放即可收听。':'已切换章节';}));
timer.addEventListener('change',()=>{deadline=null;stopAt=null;if(timer.value==='chapter'){stopAt=cfg.chapters[chapterAt(current())+1]?.start??total();$('timer-status').textContent='将在当前章节结束时暂停';}else if(timer.value!=='off'){deadline=Date.now()+Number(timer.value)*60000;checkTimer();}else clearTimer();});
setInterval(checkTimer,1000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkTimer();});
$('share').addEventListener('click',async()=>{const url=new URL(location.href);url.searchParams.set('t',String(Math.floor(current())));url.hash='player';try{await navigator.clipboard.writeText(url.href);status.textContent=`已复制${fmt(current())}的播放链接`;$('share-fallback').hidden=true;}catch(e){$('share-fallback').hidden=false;$('share-link').value=url.href;$('share-link').focus();$('share-link').select();status.textContent='请复制下方链接，朋友打开即可从此刻开始。';}});
a.addEventListener('loadedmetadata',()=>{if(pendingSeek!==null){a.currentTime=pendingSeek;pendingSeek=null;}update();});
a.addEventListener('timeupdate',()=>{checkTimer();update();if(Date.now()-lastSave>5000){store();lastSave=Date.now();}});
a.addEventListener('play',update);a.addEventListener('playing',()=>{status.textContent='正在播放';update();});
a.addEventListener('pause',()=>{status.textContent=a.ended?'本期已听完':'已暂停，进度已保留';store();update();});a.addEventListener('ended',()=>{status.textContent='本期已听完';clearTimer();store();update();});a.addEventListener('waiting',()=>{if(!a.paused)status.textContent='音频缓冲中…';});a.addEventListener('error',()=>{status.textContent='音频加载失败，可重试或下载完整音频。';update();});
const rate=Number(saved.rate);if([...speed.options].some(o=>Number(o.value)===rate)){a.playbackRate=rate;speed.value=String(rate);}a.preservesPitch=true;
if(typeof saved.volume==='number')a.volume=Math.max(0,Math.min(1,saved.volume));if(typeof saved.muted==='boolean')a.muted=saved.muted;
const raw=new URL(location.href).searchParams.get('t'),shared=raw!==null&&raw.trim()!==''?Number(raw):NaN;
if(Number.isFinite(shared)&&shared>=0){pendingSeek=Math.min(shared,cfg.duration);status.textContent=`已定位到${fmt(pendingSeek)}，点击播放。`;}else if(Number(saved.time)>3&&Number(saved.time)<cfg.duration-5){pendingSeek=Number(saved.time);status.textContent=`上次听到${fmt(pendingSeek)}，点击继续。`;}
if(pendingSeek!==null&&a.readyState>0){a.currentTime=pendingSeek;pendingSeek=null;}
root.classList.add('enhanced-audio');update();volumeUI();window.addEventListener('pagehide',store);
if('IntersectionObserver' in window)new IntersectionObserver(entries=>{$('return-audio').classList.toggle('visible',!entries[0].isIntersecting);},{threshold:0}).observe(root);
if('mediaSession' in navigator){navigator.mediaSession.metadata=new MediaMetadata({title:cfg.title,artist:'Shirley×船长',album:'船长电台',artwork:[{src:new URL(cfg.cover,location.href).href,type:'image/png'}]});for(const [name,fn] of Object.entries({play:()=>{if(a.paused)play.click();},pause:()=>a.pause(),seekbackward:d=>jump(current()-(d.seekOffset||15)),seekforward:d=>jump(current()+(d.seekOffset||15)),seekto:d=>jump(d.seekTime),previoustrack:()=>$('previous').click(),nexttrack:()=>$('next').click()})){try{navigator.mediaSession.setActionHandler(name,fn);}catch(e){}}}
})();
