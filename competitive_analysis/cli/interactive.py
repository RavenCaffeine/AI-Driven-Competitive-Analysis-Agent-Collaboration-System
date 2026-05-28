"""
Interactive CLI for Competitive Analysis Agent.

Provides a menu-driven main interface with REPL-style analysis input.
Features real-time agent progress display and colored terminal output.
"""

from __future__ import annotations

import os
import sys
import json
import time
import threading
import logging
from pathlib import Path
from typing import Optional


class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    RED     = "\033[31m"

    @staticmethod
    def disable():
        for attr in dir(Colors):
            if attr.isupper() and not attr.startswith("_"):
                setattr(Colors, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


class Spinner:
    FRAMES = ["@", "@", "@", "@", "@", "@", "@", "@", "@", "@"]

    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._message = ""
        self._step_index = 0

    def start(self, message):
        self._message = message
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def update(self, message):
        self._step_index += 1
        self._message = message

    def stop(self, final_message=""):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        if final_message:
            print(final_message)

    def _spin(self):
        frames = ["|", "/", "-", "\\"]
        idx = 0
        while not self._stop_event.is_set():
            frame = frames[idx % len(frames)]
            step = "[%d/4]" % self._step_index if self._step_index > 0 else "[...]"
            sys.stdout.write("\r%s%s%s %s%s%s %s" % (
                Colors.CYAN, frame, Colors.RESET,
                Colors.DIM, step, Colors.RESET,
                self._message
            ))
            sys.stdout.flush()
            idx += 1
            time.sleep(0.12)


BANNER = """
%s%s======================================================================
           Competitive Analysis Multi-Agent System  (v0.1.0)
======================================================================%s

%sLangGraph DAG | 4 Agent | QA Feedback Loop%s
""" % (Colors.CYAN, Colors.BOLD, Colors.RESET, Colors.DIM, Colors.RESET)

MENU = """
%s============= Main Menu =============%s

  %s[1]%s  Run Competitive Analysis
  %s[2]%s  View Historical Traces
  %s[3]%s  Run Evaluation Scenarios
  %s[4]%s  View Workflow DAG
  %s[5]%s  Show Current Config
  %s[0]%s  Exit

%s=====================================%s
""" % (
    Colors.BOLD, Colors.RESET,
    Colors.GREEN, Colors.RESET,
    Colors.BLUE, Colors.RESET,
    Colors.YELLOW, Colors.RESET,
    Colors.CYAN, Colors.RESET,
    Colors.MAGENTA, Colors.RESET,
    Colors.RED, Colors.RESET,
    Colors.BOLD, Colors.RESET,
)


def handle_analyze(config):
    print("\n%s-- Run Analysis --%s\n" % (Colors.BOLD, Colors.RESET))

    query = input("  %s?%s Query (e.g. Compare Notion vs Obsidian):\n  %s>%s " % (
        Colors.CYAN, Colors.RESET, Colors.BOLD, Colors.RESET)).strip()
    if not query:
        print("  %sNo query entered.%s" % (Colors.RED, Colors.RESET))
        return

    comp_input = input("\n  %s?%s Competitors (space-separated, Enter to auto-extract):\n  %s>%s " % (
        Colors.CYAN, Colors.RESET, Colors.BOLD, Colors.RESET)).strip()
    if comp_input:
        competitors = [c.strip() for c in comp_input.split() if c.strip()]
    else:
        competitors = [c.strip() for c in query.replace(" vs ", ",").replace(" and ", ",").split(",")]
        competitors = [c for c in competitors if c and len(c) < 50]
        print("  %sAuto-extracted: %s%s" % (Colors.DIM, ", ".join(competitors), Colors.RESET))

    if not competitors or len(competitors) < 2:
        print("  %sNeed at least 2 competitors.%s" % (Colors.RED, Colors.RESET))
        return

    fmt_input = input("\n  %s?%s Format [1] Markdown  [2] HTML  (default 1):\n  %s>%s " % (
        Colors.CYAN, Colors.RESET, Colors.BOLD, Colors.RESET)).strip()
    output_format = "html" if fmt_input == "2" else "markdown"

    print("\n  %s-- Confirm --%s" % (Colors.BOLD, Colors.RESET))
    print("  Query:       %s%s%s" % (Colors.CYAN, query, Colors.RESET))
    print("  Competitors: %s%s%s" % (Colors.GREEN, " / ".join(competitors), Colors.RESET))
    print("  Format:      %s" % output_format)
    print("  LLM:         %s (%s)" % (config.llm.provider, config.llm.model))
    confirm = input("\n  %s?%s Start? [Y/n]: " % (Colors.YELLOW, Colors.RESET)).strip().lower()
    if confirm == "n":
        print("  %sCancelled.%s" % (Colors.DIM, Colors.RESET))
        return

    print("\n" + Colors.BOLD + "-" * 50 + Colors.RESET)
    _run_analysis_with_progress(config, query, competitors, output_format)


def _run_analysis_with_progress(config, query, competitors, output_format):
    from ..workflow.graph import CompetitiveAnalysisWorkflow, build_graph

    spinner = Spinner()
    spinner.start("Initializing agents...")

    try:
        from ..tools.tavily_search import TavilySearch
        tools = {}
        if config.tools.tavily_api_key:
            tools["tavily"] = TavilySearch(config.tools.tavily_api_key)

        workflow = CompetitiveAnalysisWorkflow(config, tools=tools)
        spinner.update("Starting analysis pipeline...")

        original_collector = workflow.nodes.collector_node
        original_analyst = workflow.nodes.analyst_node
        original_writer = workflow.nodes.writer_node
        original_qa = workflow.nodes.qa_node
        original_finalize = workflow.nodes.finalize_node

        def patched_collector(state):
            spinner.update("Collector: gathering data...")
            return original_collector(state)

        def patched_analyst(state):
            spinner.update("Analyst: running comparison...")
            return original_analyst(state)

        def patched_writer(state):
            iteration = state.get("qa_iteration", 0)
            tag = " (revision #%d)" % iteration if iteration > 0 else ""
            spinner.update("Writer: generating report%s..." % tag)
            return original_writer(state)

        def patched_qa(state):
            spinner.update("QA Agent: reviewing...")
            return original_qa(state)

        def patched_finalize(state):
            spinner.update("Finalize: preparing output...")
            return original_finalize(state)

        workflow.nodes.collector_node = patched_collector
        workflow.nodes.analyst_node = patched_analyst
        workflow.nodes.writer_node = patched_writer
        workflow.nodes.qa_node = patched_qa
        workflow.nodes.finalize_node = patched_finalize

        workflow.graph = build_graph(workflow.nodes)

        final_state = workflow.run(
            query=query,
            competitors=competitors,
            output_format=output_format,
        )

        spinner.stop("  %s%sDone!%s" % (Colors.GREEN, Colors.BOLD, Colors.RESET))
        _display_results(config, final_state)

    except KeyboardInterrupt:
        spinner.stop("  %sInterrupted%s" % (Colors.YELLOW, Colors.RESET))
    except Exception as e:
        spinner.stop("  %sFailed: %s%s" % (Colors.RED, e, Colors.RESET))
        logging.getLogger().debug("Analysis error", exc_info=True)


def _display_results(config, final_state):
    report = final_state.get("final_report", "")
    metrics = final_state.get("report_metrics", {})
    qa_iter = final_state.get("qa_iteration", 0)

    print("\n%s-- Results --%s\n" % (Colors.BOLD, Colors.RESET))

    if report:
        out_dir = Path(config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save Markdown
        md_path = out_dir / "report.md"
        md_path.write_text(report, encoding="utf-8")

        # Save HTML
        html_path = None
        html_report = final_state.get("html_report", "")
        if html_report:
            html_path = out_dir / "report.html"
            html_path.write_text(html_report, encoding="utf-8")
        else:
            try:
                from ..report.renderer import ReportRenderer
                renderer = ReportRenderer(output_dir=str(out_dir))
                html_path = renderer.render(final_state)
            except Exception as e:
                logging.getLogger().debug("HTML render fallback failed: %s", e)

        print("  Markdown:  %s%s%s" % (Colors.CYAN, md_path, Colors.RESET))
        if html_path and html_path.exists():
            print("  HTML:      %s%s%s" % (Colors.CYAN, html_path, Colors.RESET))
        print("  Sections:  %s" % metrics.get("section_count", "?"))
        print("  Citations: %s" % metrics.get("citation_count", "?"))
        print("  QA rounds: %s" % qa_iter)
        print("  Length:    %d chars" % len(report))

        preview_lines = report.split("\n")[:8]
        print("\n  %s-- Preview --%s" % (Colors.DIM, Colors.RESET))
        for line in preview_lines:
            print("  %s%s%s" % (Colors.DIM, line[:80], Colors.RESET))
        if len(report.split("\n")) > 8:
            print("  %s...(see full report files)%s" % (Colors.DIM, Colors.RESET))

        # Offer screenshot
        if html_path and html_path.exists():
            ss = input(
                "\n  %s?%s Generate screenshot? [1] PNG  [2] PDF  [Enter skip]: " % (
                    Colors.CYAN, Colors.RESET)
            ).strip()
            if ss in ("1", "2"):
                fmt = "pdf" if ss == "2" else "png"
                print("  %sCapturing...%s" % (Colors.DIM, Colors.RESET))
                try:
                    from ..report.renderer import ReportRenderer
                    renderer = ReportRenderer(output_dir=str(out_dir))
                    ss_path = renderer.screenshot(html_path, output_format=fmt)
                    if ss_path:
                        print("  Screenshot: %s%s%s" % (Colors.GREEN, ss_path, Colors.RESET))
                    else:
                        print("  %sScreenshot unavailable. Install:%s" % (Colors.YELLOW, Colors.RESET))
                        print("    %spip install playwright && playwright install chromium%s" % (Colors.DIM, Colors.RESET))
                except Exception as e:
                    print("  %sScreenshot failed: %s%s" % (Colors.RED, e, Colors.RESET))
    else:
        print("  %sNo report generated. Check logs.%s" % (Colors.RED, Colors.RESET))

    trace = final_state.get("trace", {})
    if trace.get("run_id"):
        trace_dir = Path(config.output_dir) / "runs" / trace["run_id"]
        print("\n  Trace ID:  %s%s%s" % (Colors.DIM, trace.get("run_id", "?"), Colors.RESET))
        print("  Trace dir: %s%s%s" % (Colors.DIM, trace_dir, Colors.RESET))

    print()


def handle_trace(config):
    print("\n%s-- Historical Traces --%s\n" % (Colors.BOLD, Colors.RESET))

    runs_dir = Path(config.output_dir) / "runs"
    if not runs_dir.exists():
        print("  %sNo runs yet.%s" % (Colors.DIM, Colors.RESET))
        return

    runs = sorted(runs_dir.iterdir(), reverse=True)
    if not runs:
        print("  %sNo runs yet.%s" % (Colors.DIM, Colors.RESET))
        return

    for i, run_path in enumerate(runs[:10], 1):
        trace_file = run_path / "trace.json"
        if trace_file.exists():
            trace = json.loads(trace_file.read_text(encoding="utf-8"))
            query = trace.get("query", "?")[:50]
            ts = trace.get("start_time", "?")[:19]
            provider = trace.get("provider", "?")
            print("  %s[%d]%s %s  %s%s%s  (%s)" % (
                Colors.GREEN, i, Colors.RESET, ts, Colors.CYAN, query, Colors.RESET, provider))
        else:
            print("  %s[%d]%s %s" % (Colors.GREEN, i, Colors.RESET, run_path.name))

    choice = input("\n  %s?%s Select trace # (Enter to go back): " % (Colors.CYAN, Colors.RESET)).strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(runs[:10]):
        return

    run_path = runs[int(choice) - 1]
    trace_file = run_path / "trace.json"
    if not trace_file.exists():
        print("  %sTrace file not found%s" % (Colors.RED, Colors.RESET))
        return

    trace = json.loads(trace_file.read_text(encoding="utf-8"))

    print("\n  %s-- Trace Detail --%s" % (Colors.BOLD, Colors.RESET))
    print("  Run ID:   %s" % trace.get("run_id", "?"))
    print("  Query:    %s" % trace.get("query", "?"))
    print("  Provider: %s / %s" % (trace.get("provider", "?"), trace.get("model", "?")))
    print("  Started:  %s" % trace.get("start_time", "?"))
    print("  Ended:    %s" % trace.get("end_time", "?"))

    events = trace.get("events", [])
    if events:
        print("\n  %sTimeline (%d events):%s" % (Colors.BOLD, len(events), Colors.RESET))
        for evt in events[:20]:
            ts = evt.get("timestamp", "?")[-12:]
            etype = evt.get("event_type", "?")
            name = evt.get("name", "?")
            latency = evt.get("latency_ms", "")
            lat_str = " (%sms)" % latency if latency else ""
            color = Colors.GREEN if "start" in etype else Colors.YELLOW
            print("    %s*%s %s  %s: %s%s" % (color, Colors.RESET, ts, etype, name, lat_str))
        if len(events) > 20:
            print("    %s...%d more events%s" % (Colors.DIM, len(events) - 20, Colors.RESET))

    print()


def handle_eval(config):
    print("\n%s-- Evaluation --%s\n" % (Colors.BOLD, Colors.RESET))

    from ..evaluation.scenarios import SCENARIOS

    scenario_names = list(SCENARIOS.keys())
    for i, name in enumerate(scenario_names, 1):
        s = SCENARIOS[name]
        desc = s.get("description", name)
        comps = ", ".join(s.get("competitors", []))
        print("  %s[%d]%s %s" % (Colors.GREEN, i, Colors.RESET, name))
        print("      %s%s - %s%s" % (Colors.DIM, desc, comps, Colors.RESET))

    print("  %s[A]%s Run all scenarios" % (Colors.YELLOW, Colors.RESET))

    choice = input("\n  %s?%s Select (Enter to go back): " % (Colors.CYAN, Colors.RESET)).strip()

    if choice.lower() == "a":
        scenario_name = "all"
    elif choice.isdigit() and 1 <= int(choice) <= len(scenario_names):
        scenario_name = scenario_names[int(choice) - 1]
    else:
        return

    print("\n  %sRunning evaluation (requires LLM API Key)...%s" % (Colors.DIM, Colors.RESET))

    try:
        from ..evaluation.runner import run_scenario, run_all_scenarios
        from ..workflow.graph import CompetitiveAnalysisWorkflow
        from ..tools.tavily_search import TavilySearch

        tools = {}
        if config.tools.tavily_api_key:
            tools["tavily"] = TavilySearch(config.tools.tavily_api_key)
        workflow = CompetitiveAnalysisWorkflow(config, tools=tools)

        if scenario_name == "all":
            results = run_all_scenarios(workflow)
        else:
            results = [run_scenario(scenario_name, workflow)]

        for r in results:
            print("\n  %sScenario: %s%s" % (Colors.BOLD, r.get("scenario", "?"), Colors.RESET))
            score = r.get("overall_score", 0)
            color = Colors.GREEN if score >= 0.7 else Colors.YELLOW if score >= 0.4 else Colors.RED
            print("  Score: %s%.2f%s" % (color, score, Colors.RESET))

            dims = r.get("dimensions", {})
            for dim, val in dims.items():
                bar_len = int(val * 20)
                bar = "#" * bar_len + "." * (20 - bar_len)
                print("    %-25s %s %.2f" % (dim, bar, val))

    except Exception as e:
        print("  %sEvaluation failed: %s%s" % (Colors.RED, e, Colors.RESET))

    print()


def handle_visualize(config):
    print("\n%s-- Workflow DAG (Mermaid) --%s\n" % (Colors.BOLD, Colors.RESET))
    print("""%s  graph TD
    START --> collector[Collector Agent]
    collector --> analyst[Analyst Agent]
    analyst --> writer[Writer Agent]
    writer --> qa_agent[QA Agent]
    qa_agent -->|accept| finalize[Finalize]
    qa_agent -->|missing data| collector
    qa_agent -->|analysis issues| analyst
    qa_agent -->|writing issues| writer
    finalize --> END%s""" % (Colors.CYAN, Colors.RESET))

    print("""
  %sNodes:%s
    %s* Collector%s  Data gathering (Tavily search + scraping)
    %s* Analyst%s    Comparison analysis (features/pricing/SWOT)
    %s* Writer%s     Report generation (Markdown/HTML)
    %s* QA Agent%s   Quality review + feedback routing
    %s* Finalize%s   Output packaging + trace saving
""" % (
        Colors.BOLD, Colors.RESET,
        Colors.GREEN, Colors.RESET,
        Colors.BLUE, Colors.RESET,
        Colors.YELLOW, Colors.RESET,
        Colors.RED, Colors.RESET,
        Colors.MAGENTA, Colors.RESET,
    ))


def handle_config(config):
    print("\n%s-- Current Config --%s\n" % (Colors.BOLD, Colors.RESET))

    print("  %sLLM:%s" % (Colors.BOLD, Colors.RESET))
    print("    Provider:    %s%s%s" % (Colors.CYAN, config.llm.provider, Colors.RESET))
    print("    Model:       %s" % config.llm.model)
    print("    Temperature: %s" % config.llm.temperature)
    print("    Max Tokens:  %s" % config.llm.max_tokens)
    if config.llm.base_url:
        print("    Base URL:    %s" % config.llm.base_url)

    api_key = config.llm.api_key
    if api_key and len(api_key) > 10:
        masked = api_key[:6] + "..." + api_key[-4:]
    else:
        masked = "(not set)"
    print("    API Key:     %s%s%s" % (Colors.DIM, masked, Colors.RESET))

    print("\n  %sTools:%s" % (Colors.BOLD, Colors.RESET))
    tavily = config.tools.tavily_api_key
    if tavily:
        tavily_status = "%sConfigured%s" % (Colors.GREEN, Colors.RESET)
    else:
        tavily_status = "%sNot configured%s" % (Colors.RED, Colors.RESET)
    print("    Tavily:      %s" % tavily_status)

    print("\n  %sWorkflow:%s" % (Colors.BOLD, Colors.RESET))
    print("    QA retries:  %s" % config.max_qa_retries)
    print("    Output dir:  %s" % config.output_dir)
    print("    Log level:   %s" % config.log_level)

    print()


def run_interactive(env_path=None, log_level="WARNING"):
    from ..utils.config import load_config
    from ..utils.logger import setup_logger

    config = load_config(env_path)
    setup_logger(level=log_level)

    print(BANNER)

    if not config.llm.api_key:
        print("  %sNote: No LLM API Key detected. Copy .env.example to .env and configure.%s" % (
            Colors.YELLOW, Colors.RESET))
        print("  %sSome features (DAG view, trace view) still work without it.%s\n" % (
            Colors.DIM, Colors.RESET))

    handlers = {
        "1": handle_analyze,
        "2": handle_trace,
        "3": handle_eval,
        "4": handle_visualize,
        "5": handle_config,
    }

    while True:
        print(MENU)
        try:
            choice = input("  %sSelect [0-5]:%s " % (Colors.BOLD, Colors.RESET)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  %sBye!%s\n" % (Colors.DIM, Colors.RESET))
            break

        if choice == "0":
            print("\n  %sBye!%s\n" % (Colors.DIM, Colors.RESET))
            break
        elif choice in handlers:
            try:
                handlers[choice](config)
            except KeyboardInterrupt:
                print("\n  %sInterrupted%s" % (Colors.YELLOW, Colors.RESET))
            except Exception as e:
                print("\n  %sError: %s%s" % (Colors.RED, e, Colors.RESET))
                logging.getLogger().debug("Handler error", exc_info=True)
        else:
            print("  %sInvalid choice, enter 0-5%s" % (Colors.RED, Colors.RESET))
