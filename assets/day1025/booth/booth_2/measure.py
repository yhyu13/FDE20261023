#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把测量脚本注入 slides.html，生成 _shots/m.html 供 headless Edge 量高。"""
import sys, io

MEASURE_S3 = """<script>window.addEventListener("load",()=>{setTimeout(()=>{
  document.querySelectorAll(".pg").forEach(p=>p.classList.toggle("on",p.dataset.id==="s3"));
  const pg=document.querySelector(".pg.on");
  pg.querySelectorAll("[data-cue]").forEach(e=>e.classList.add("on"));
  const out=[];
  pg.querySelectorAll(".main .panel").forEach(p=>{
    const ph=p.querySelector(".ph"), pb=p.querySelector(".pb");
    const name=ph?ph.textContent.trim().slice(0,6):"pool";
    out.push(name+": panel="+p.offsetHeight+" pbClient="+(pb?pb.clientHeight:"-")+" pbScroll="+(pb?pb.scrollHeight:"-"));
  });
  document.title=out.join(" || ");
},250);});</script></body>"""

MEASURE_S2 = """<script>window.addEventListener("load",()=>{setTimeout(()=>{
  document.querySelectorAll(".pg").forEach(p=>p.classList.toggle("on",p.dataset.id==="s2"));
  const pg=document.querySelector(".pg.on");
  pg.querySelectorAll("[data-cue]").forEach(e=>e.classList.add("on"));
  const d=document.getElementById("cq-detail");
  let worst="",worstH=0;
  CQ.forEach(c=>{sel=c.id;cqShow();const h=d.scrollHeight;if(h>worstH){worstH=h;worst=c.id;}});
  sel="CQ04";cqShow();
  const out=["s2 worst="+worst+"/"+worstH+" pbClient="+d.clientHeight];
  pg.querySelectorAll(".main .panel").forEach(p=>{
    const ph=p.querySelector(".ph");
    out.push((ph?ph.textContent.trim().slice(0,4):"?")+"="+p.offsetHeight);
  });
  // 闸门面板内部构成
  const ev=pg.querySelector('.panel[data-cue="ev"]');
  if(ev){const g=ev.querySelector(".gates3"),r=ev.querySelector(".rc3"),m=ev.querySelector(".mx")||document.querySelector(".mx");
    out.push("gates3="+(g?g.offsetHeight:"-")+" rc3="+(r?r.offsetHeight:"-")+" mxTable="+(m?m.offsetHeight:"-"));}
  document.title=out.join(" | ");
},250);});</script></body>"""

MEASURE = {"s2": MEASURE_S2, "s3": MEASURE_S3}

which = sys.argv[1] if len(sys.argv) > 1 else "s2"
src = io.open("slides.html", encoding="utf-8").read()
out = src.replace("</body>", MEASURE[which])
io.open("_shots/m.html", "w", encoding="utf-8").write(out)
print("ok", which)
