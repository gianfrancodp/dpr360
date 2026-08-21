from __future__ import annotations
from collections import deque
from pathlib import Path
import json, os
import streamlit as st
from dpr360 import __version__
from dpr360.logger import UsageLogger
from dpr360.models import PipelineContext
from dpr360.picker import choose_directory, choose_file
from dpr360.pipeline import PipelineRunner, ALL_STEPS
from dpr360.scanning import list_dngs
from dpr360.settings import load_config, save_tool_override
from dpr360.smoke import smoke_test
from dpr360.tools import detect_tools, install_exiftool_official, install_winget

ROOT=Path(os.environ.get("DPR360_HOME", Path(__file__).resolve().parent)).resolve()
cfg=load_config(ROOT)
logcfg=cfg.get("logging",{})
logger=UsageLogger(
    ROOT/logcfg.get("log_dir","./logs"),
    logcfg.get("enabled",True),
    logcfg.get("include_paths",False),
    logcfg.get("diagnostic_mode",False),
    logcfg.get("include_sensitive_metadata",False),
)
st.set_page_config(page_title="DronePanoRAW 360",layout="wide")
logger.event("app_open",version=__version__)
st.title("DronePanoRAW 360")
st.caption("Pano Mode → RAW → 360° · local-first RAW panorama workflow")

for key,default in {"source_dir":"","project_dir":"","smoke_dng":"","chat":[]}.items():
    st.session_state.setdefault(key,default)

def tools_ready(tools):
    required=["exiftool","rawtherapee","pto_gen","cpfind","cpclean","autooptimiser","pano_modify","nona","enblend"]
    return [x for x in required if not tools.get(x)]

def make_runner():
    tools=detect_tools(ROOT,cfg)
    src=Path(st.session_state.source_dir);project=Path(st.session_state.project_dir)
    ctx=PipelineContext(src,project,tools,cfg,logger);ctx.ensure_dirs()
    return PipelineRunner(ctx,ALL_STEPS),ctx,tools

def state_rows(runner):
    icons={"pending":"○","running":"▶","completed":"✓","completed_with_warnings":"⚠","failed":"✗","retry":"↻","skipped":"⏭"}
    return [{"":"%s"%icons.get(runner.state.status(s.name),"○"),"Step":s.label,"ID":s.name,"Stato":runner.state.status(s.name),"Peso":f"{s.weight*100:.0f}%"} for s in ALL_STEPS]

def execute_pipeline(mode="all",single_step=None):
    if not st.session_state.source_dir or not st.session_state.project_dir:
        st.error("Seleziona prima cartella DNG e cartella progetto.");return
    runner,ctx,tools=make_runner();missing=tools_ready(tools)
    if missing: st.error("Tool mancanti: "+", ".join(missing));return
    logs=deque(maxlen=300)
    st.markdown("### Esecuzione")
    overall=st.progress(runner.overall_fraction(),text="Avanzamento generale")
    stepbar=st.progress(0.0,text="Processo corrente")
    status=st.empty()
    with st.expander("Log esecuzione · espandi/comprimi liberamente",expanded=False):
        logbox=st.empty()
    def live(line):
        logs.append(line);logbox.code("\n".join(logs),language=None)
    def prog(ev):
        overall.progress(max(0,min(1,ev.overall_fraction)),text=f"Pipeline · {ev.overall_fraction*100:.1f}%")
        stepbar.progress(max(0,min(1,ev.step_fraction)),text=f"{ev.step_label} · {ev.step_fraction*100:.1f}%")
        status.info(ev.message or ev.step_label)
    ctx.live_log_callback=live;runner.ui_progress_callback=prog
    if mode=="all":result,_=runner.run_all(False)
    elif mode=="resume":result,_=runner.run_all(True)
    else:result=runner.run_step(single_step)
    st.session_state.last_pipeline_result=result.to_dict()
    if result.returncode==0:
        if result.warnings:
            st.warning(result.message)
            with st.expander("Warning della pipeline", expanded=False):
                for w in result.warnings:
                    st.write("• "+w)
        else:
            st.success(result.message)
    else:st.error(f"STOP · {result.name} · exit code {result.returncode} · {result.message}")
    overall.progress(runner.overall_fraction(),text=f"Pipeline · {runner.overall_fraction()*100:.1f}%")
    st.dataframe(state_rows(runner), width="stretch", hide_index=True)
    if result.details:st.json(result.details)

project_tab,pipeline_tab,tools_tab,smoke_tab,logs_tab,guide_tab,about_tab=st.tabs(["Progetto","Pipeline","Tool Windows","Smoke test","Log","Guida","About"])

with project_tab:
    st.subheader("Input e progetto")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**Cartella sorgente DNG**")
        if st.button("Apri Esplora file · DNG", width="stretch"):
            chosen=choose_directory(st.session_state.source_dir)
            logger.event("ui_picker",kind="source_dir",selected=bool(chosen))
            if chosen:st.session_state.source_dir=chosen;st.rerun()
        st.session_state.source_dir=st.text_input("Percorso sorgente (fallback)",value=st.session_state.source_dir)
    with c2:
        st.markdown("**Cartella progetto/output**")
        if st.button("Apri Esplora file · progetto", width="stretch"):
            chosen=choose_directory(st.session_state.project_dir)
            logger.event("ui_picker",kind="project_dir",selected=bool(chosen))
            if chosen:st.session_state.project_dir=chosen;st.rerun()
        st.session_state.project_dir=st.text_input("Percorso progetto (fallback)",value=st.session_state.project_dir)
    if st.session_state.source_dir:
        dngs=list_dngs(Path(st.session_state.source_dir));st.metric("DNG trovati",len(dngs))
        expected=cfg.get("pipeline",{}).get("expected_dng_count",33)
        if len(dngs)!=expected:st.warning(f"Attesi {expected} DNG, trovati {len(dngs)}. Nessun file viene duplicato dalla scansione case-insensitive.")
        st.dataframe({"File":[p.name for p in dngs]}, width="stretch", hide_index=True)

with pipeline_tab:
    st.subheader("Pipeline")
    if st.session_state.source_dir and st.session_state.project_dir:
        runner,ctx,tools=make_runner();missing=tools_ready(tools)
        if missing:st.error("Tool mancanti: "+", ".join(missing))
        else:st.success("Toolchain pronta")
        st.dataframe(state_rows(runner), width="stretch", hide_index=True)
        st.progress(runner.overall_fraction(),text=f"Avanzamento salvato · {runner.overall_fraction()*100:.1f}%")
        b1,b2,b3=st.columns(3)
        if b1.button("▶ RUN ALL", type="primary", width="stretch"):logger.event("ui_click",control="run_all");execute_pipeline("all")
        if b2.button("↻ RESUME", width="stretch"):logger.event("ui_click",control="resume");execute_pipeline("resume")
        if b3.button("Reset checkpoint", width="stretch"):runner.reset();logger.event("ui_click",control="reset_state");st.rerun()
        with st.expander("Esegui un singolo step"):
            for s in ALL_STEPS:
                c1,c2=st.columns([3,1]);c1.write(f"{s.label} (`{s.name}`)")
                if c2.button("Esegui", key=f"run_{s.name}", width="stretch"):execute_pipeline("single",s.name)
        last=st.session_state.get("last_pipeline_result")
        if last:
            st.markdown("#### Ultimo risultato");st.json(last)
    else:st.info("Configura prima le cartelle nella scheda Progetto.")

with tools_tab:
    st.subheader("Dipendenze Windows")
    tools=detect_tools(ROOT,cfg)
    st.dataframe([{"Tool":k,"Percorso":v or "MANCANTE"} for k,v in tools.items()], width="stretch", hide_index=True)
    if st.button("Rileva di nuovo"):st.rerun()
    c1,c2,c3=st.columns(3)
    if not tools.get("exiftool") and c1.button("Installa ExifTool portable"):
        try:p=install_exiftool_official(ROOT,logger);st.success(p);st.rerun()
        except Exception as e:st.error(str(e))
    if not tools.get("rawtherapee") and c2.button("Installa RawTherapee · WinGet"):
        ok,msg=install_winget(cfg.get("winget",{}).get("rawtherapee_id","RawTherapee.RawTherapee"),logger=logger,tool="rawtherapee");st.success(msg) if ok else st.error(msg)
    if not tools.get("pto_gen") and c3.button("Installa Hugin · WinGet"):
        ok,msg=install_winget(name="Hugin",logger=logger,tool="hugin");st.success(msg) if ok else st.error(msg)
    st.markdown("#### Override manuale con Esplora file")
    for label,key,exe in [("ExifTool","exiftool","exiftool.exe"),("RawTherapee","rawtherapee","rawtherapee-cli.exe")]:
        if st.button(f"Seleziona {label}…",key=f"pick_{key}"):
            p=choose_file(filetypes=[(exe,exe),("Executables","*.exe")]);
            if p:save_tool_override(ROOT,key,p);st.rerun()
    if st.button("Seleziona cartella bin Hugin…"):
        p=choose_directory()
        if p:save_tool_override(ROOT,"hugin_bin",p);st.rerun()

with smoke_tab:
    st.subheader("Smoke test su un DNG")
    if st.button("Seleziona DNG di test…"):
        p=choose_file(st.session_state.smoke_dng,[("DNG","*.dng;*.DNG"),("All","*.*")]);
        if p:st.session_state.smoke_dng=p;st.rerun()
    st.session_state.smoke_dng=st.text_input("DNG (fallback)",value=st.session_state.smoke_dng)
    if st.button("Esegui smoke test",type="primary"):
        tools=detect_tools(ROOT,cfg);need=[x for x in ["exiftool","rawtherapee","pto_gen","nona"] if not tools.get(x)]
        if need:st.error("Mancano: "+", ".join(need))
        elif not Path(st.session_state.smoke_dng).exists():st.error("Seleziona un DNG valido.")
        else:
            lines=deque(maxlen=150)
            with st.expander("Log smoke test",expanded=True):box=st.empty()
            try:
                smoke_test(Path(st.session_state.smoke_dng),ROOT/"outputs"/"00_smoke_test",tools,logger,lambda x:(lines.append(x),box.code("\n".join(lines))))
                st.success("Smoke test superato.")
            except Exception as e:st.error(str(e))

with logs_tab:
    st.subheader("Log locali")
    files=sorted((ROOT/"logs").glob("usage_*.jsonl"),reverse=True)
    if not files:st.info("Nessun log disponibile.")
    else:
        selected=st.selectbox("File log",files,format_func=lambda p:p.name)
        raw=selected.read_text(encoding="utf-8",errors="replace");lines=raw.splitlines()
        st.code("\n".join(lines[-120:]),language="json")
        st.download_button("Scarica log",selected.read_bytes(),file_name=selected.name)
        st.caption("Privacy-safe di default: path, GPS e identificativi camera sono oscurati. Abilita diagnostic_mode solo per debugging mirato.")

with guide_tab:
    st.subheader("Guida / comandi")
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):st.write(m["content"])
    prompt=st.chat_input("Es.: status, cosa faccio ora, run all, resume")
    if prompt:
        st.session_state.chat.append({"role":"user","content":prompt});q=prompt.strip().lower()
        if q in {"run all","runall","esegui tutto"}:
            answer="Avvio RUN ALL. La pipeline si fermerà automaticamente al primo exit code diverso da 0."
            st.session_state.chat.append({"role":"assistant","content":answer});st.write(answer);execute_pipeline("all")
        elif q in {"resume","riprendi"}:
            answer="Riprendo dal primo step non completato."
            st.session_state.chat.append({"role":"assistant","content":answer});st.write(answer);execute_pipeline("resume")
        elif "status" in q or "stato" in q:
            if st.session_state.source_dir and st.session_state.project_dir:
                runner,_,_=make_runner();answer=" · ".join(f"{s.name}: {runner.state.status(s.name)}" for s in ALL_STEPS)
            else:answer="Seleziona prima sorgente DNG e cartella progetto."
            st.session_state.chat.append({"role":"assistant","content":answer});st.write(answer)
        else:
            answer="Posso guidarti sulla pipeline. Comandi rapidi: `run all`, `resume`, `status`. Per cambiare input usa la scheda Progetto."
            st.session_state.chat.append({"role":"assistant","content":answer});st.write(answer)

with about_tab:
    st.subheader("About")
    st.write(f"**DronePanoRAW 360 (DPR360)** · version {__version__}")
    st.write("Licenza: **GPL-3.0-or-later** · strong copyleft/share-alike per software.")
    st.write("Copyright © 2026 Gianfranco Di Pietro.")
    st.write("Free and open source. Designed by drone photographers, for drone photographers.")
    st.write("Author: Gianfranco Di Pietro · https://gianfrancodp.github.io")
