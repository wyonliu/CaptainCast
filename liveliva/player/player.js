(() => {
 'use strict';
 const cfg=JSON.parse(document.getElementById('episode-config').textContent);
 const a=document.getElementById('episode-audio'),root=document.getElementById('player');
 const play=document.getElementById('play'),seek=document.getElementById('seek'),speed=document.getElementById('speed'),volume=document.getElementById('volume'),mute=document.getElementById('mute'),status=document.getElementById('audio-status');
 const $=id=>document.getElementById(id),key='captaincast-liveliva-v7-listening';
 const fmt=s=>{s=Math.max(0,Math.floor(Number(s)||0));return `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;};
 let saved={},lastSave=0,pendingSeek=null,dragging=false;
 try{saved=JSON.parse(localStorage.getItem(key)||'{}');}catch(e){}
 const total=()=>Number.isFinite(a.duration)&&a.duration>0?a.duration:cfg.duration;
 const chapter=()=>{let i=0;cfg.chapters.forEach((c,n)=>{if(a.currentTime>=c.start-.1)i=n;});return i;};
 function store(){try{localStorage.setItem(key,JSON.stringify({time:a.ended?0:(pendingSeek??a.currentTime),rate:a.playbackRate}));}catch(e){}}
 function update(){const t=a.currentTime||0,d=total();seek.max=d;if(!dragging)seek.value=t;$('elapsed').textContent=fmt(dragging?seek.value:t);$('duration').textContent=fmt(d);seek.setAttribute('aria-valuetext',`${fmt(dragging?seek.value:t)}，总时长${fmt(d)}`);$('played-clip').setAttribute('width',String(600*(dragging?seek.value:t)/d));const c=cfg.chapters[chapter()];$('chapter-index').textContent=c.chapter;$('chapter-title').textContent=c.title;$('chapter-read').href='script.html#ch-'+c.chapter;document.querySelectorAll('[data-chapter]').forEach((b,i)=>b.setAttribute('aria-current',i===chapter()?'true':'false'));play.classList.toggle('playing',!a.paused);play.setAttribute('aria-label',a.paused?'播放完整对话':'暂停播放');play.setAttribute('aria-pressed',String(!a.paused));}
 function jump(t){const target=Math.max(0,Math.min(total(),Number(t)||0));if(a.readyState===0){pendingSeek=target;a.load();}else a.currentTime=target;seek.value=target;update();store();}
 play.addEventListener('click',async()=>{if(!a.paused){a.pause();return;}status.textContent='正在载入音频…';try{await a.play();status.textContent='正在播放';}catch(e){status.textContent='音频暂时未能播放，请重试或下载收听。';update();}});
 document.querySelectorAll('[data-skip]').forEach(b=>b.addEventListener('click',()=>jump(a.currentTime+Number(b.dataset.skip))));
 $('previous').addEventListener('click',()=>{const i=chapter();jump(a.currentTime-cfg.chapters[i].start>3?cfg.chapters[i].start:cfg.chapters[Math.max(0,i-1)].start);});
 $('next').addEventListener('click',()=>jump(cfg.chapters[Math.min(cfg.chapters.length-1,chapter()+1)].start));
 seek.addEventListener('input',()=>{dragging=true;update();});seek.addEventListener('change',()=>{const t=Number(seek.value);dragging=false;jump(t);});
 speed.addEventListener('change',()=>{a.playbackRate=Number(speed.value);store();});
 function volumeUI(){mute.setAttribute('aria-label',a.muted?'取消静音':'静音');mute.setAttribute('aria-pressed',String(a.muted));mute.style.opacity=a.muted?'.45':'1';}
 mute.addEventListener('click',()=>{a.muted=!a.muted;volumeUI();});volume.addEventListener('input',()=>{a.volume=Number(volume.value);a.muted=a.volume===0;volumeUI();});
 document.querySelectorAll('[data-chapter]').forEach(b=>b.addEventListener('click',()=>{jump(cfg.chapters[Number(b.dataset.chapter)].start);status.textContent=a.paused?'已定位，点击播放即可收听。':'已切换章节';}));
 a.addEventListener('loadedmetadata',()=>{if(pendingSeek!==null){a.currentTime=pendingSeek;pendingSeek=null;}update();});
 a.addEventListener('timeupdate',()=>{update();if(Date.now()-lastSave>5000){store();lastSave=Date.now();}});
 a.addEventListener('play',()=>{update();});a.addEventListener('playing',()=>{status.textContent='正在播放';update();});
 a.addEventListener('pause',()=>{status.textContent=a.ended?'本期已听完':'已暂停，进度已保留';store();update();});a.addEventListener('ended',()=>{status.textContent='本期已听完';store();update();});a.addEventListener('waiting',()=>{if(!a.paused)status.textContent='音频缓冲中…';});a.addEventListener('error',()=>{status.textContent='音频加载失败，可重试或下载完整音频。';update();});
 const rate=Number(saved.rate);if([...speed.options].some(o=>Number(o.value)===rate)){a.playbackRate=rate;speed.value=String(rate);}
 if(Number(saved.time)>3&&Number(saved.time)<cfg.duration-5){pendingSeek=Number(saved.time);status.textContent=`已保留上次进度${fmt(pendingSeek)}，点击播放继续。`;}
 if(pendingSeek!==null&&a.readyState>0){a.currentTime=pendingSeek;pendingSeek=null;}
 root.classList.add('enhanced-audio');update();volumeUI();
 window.addEventListener('pagehide',store);
 if('IntersectionObserver' in window)new IntersectionObserver(entries=>{$('return-audio').classList.toggle('visible',!entries[0].isIntersecting);},{threshold:0}).observe(root);
 if('mediaSession' in navigator){navigator.mediaSession.metadata=new MediaMetadata({title:cfg.title,artist:'Shirley×船长',album:'船长电台'});for(const [name,fn] of Object.entries({play:()=>{if(a.paused)play.click();},pause:()=>a.pause(),seekbackward:d=>jump(a.currentTime-(d.seekOffset||15)),seekforward:d=>jump(a.currentTime+(d.seekOffset||15)),seekto:d=>jump(d.seekTime),previoustrack:()=>$('previous').click(),nexttrack:()=>$('next').click()})){try{navigator.mediaSession.setActionHandler(name,fn);}catch(e){}}}
 $('copy')?.addEventListener('click',async()=>{const el=$('wechat-content')||document.querySelector('.article');try{await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([el.outerHTML],{type:'text/html'}),'text/plain':new Blob([el.innerText],{type:'text/plain'})})]);$('status').textContent='正文排版已复制。';}catch(e){const r=document.createRange();r.selectNodeContents(el);const s=window.getSelection();s.removeAllRanges();s.addRange(r);$('status').textContent='正文已选中，可复制。';}});
})();
