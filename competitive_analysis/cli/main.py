"""
CLI for Competitive Analysis Agent.

Usage:
    python main.py                         # Interactive menu (default)
    python main.py interactive             # Same
    python main.py analyze "Compare Notion vs Obsidian" --competitors Notion Obsidian
    python main.py eval --scenario saas_pm_tools
    python main.py trace --run-id <run_id>
    python main.py visualize
"""

from __future__ import annotations

import argparse
import json
import sys
import logging
from pathlib import Path


def build_tools(config):
    """Build tool instances from config."""
    from ..tools.tavily_search import TavilySearch
    tools = {}
    if config.tools.tavily_api_key:
        tools["tavily"] = TavilySearch(config.tools.tavily_api_key)
    return tools


def cmd_analyze(args, config):
    """Run a competitive analysis."""
    from ..workflow.graph import CompetitiveAnalysisWorkflow

    logger = logging.getLogger("competitive_analysis")
    logger.info("Starting competitive analysis: %s", args.query)

    tools = build_tools(config)
    workflow = CompetitiveAnalysisWorkflow(config, tools=tools)

    competitors = args.competitors
    if not competitors:
        competitors = [c.strip() for c in args.query.replace(" vs ", ",").replace(" and ", ",").split(",")]
        competitors = [c for c in competitors if c and len(c) < 50]

    final_state = workflow.run(
        query=args.query,
        competitors=competitors,
        output_format=args.format,
    )

    report = final_state.get("final_report", "")
    if report:
        out_dir = Path(config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save Markdown
        md_path = out_dir / "report.md"
        md_path.write_text(report, encoding="utf-8")
        print("\nMarkdown saved to: " + str(md_path))

        # Save HTML (polished version)
        try:
            from ..report.renderer import ReportRenderer
            renderer = ReportRenderer(output_dir=str(out_dir))
            html_path = renderer.render(final_state)
            print("HTML saved to: " + str(html_path))
        except Exception as e:
            logging.getLogger().warning("HTML render failed: %s", e)

        metrics = final_state.get("report_metrics", {})
        print("Sections: " + str(metrics.get("section_count", "?")))
        print("Citations: " + str(metrics.get("citation_count", "?")))
        print("QA iterations: " + str(final_state.get("qa_iteration", 0)))
    else:
        print("No report generated. Check logs for errors.")


def cmd_eval(args, config):
    """Run evaluation scenarios."""
    from ..evaluation.runner import run_scenario, run_all_scenarios
    from ..workflow.graph import CompetitiveAnalysisWorkflow

    tools = build_tools(config)
    workflow = CompetitiveAnalysisWorkflow(config, tools=tools)

    if args.scenario == "all":
        results = run_all_scenarios(workflow)
    else:
        results = [run_scenario(args.scenario, workflow)]

    for r in results:
        print(json.dumps(r, indent=2, default=str))


def cmd_trace(args, config):
    """View a trace."""
    trace_path = Path(config.output_dir) / "runs" / args.run_id / "trace.json"
    if not trace_path.exists():
        print("Trace not found: " + str(trace_path))
        return
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if args.events:
        for event in trace.get("events", []):
            ts = event.get("timestamp", "?")
            etype = event.get("event_type", "?")
            name = event.get("name", "?")
            lat = event.get("latency_ms", "?")
            status = event.get("status", "ok")
            print("[%s] %s: %s (%sms) %s" % (ts, etype, name, lat, status))
    else:
        print(json.dumps(trace, indent=2, default=str)[:5000])


def cmd_visualize(args, config):
    """Print workflow DAG as Mermaid diagram (no LLM needed)."""
    print("""graph TD
    START --> collector[Collector Agent]
    collector --> analyst[Analyst Agent]
    analyst --> writer[Writer Agent]
    writer --> qa_agent[QA Agent]
    qa_agent -->|accept| finalize[Finalize]
    qa_agent -->|missing data| collector
    qa_agent -->|analysis issues| analyst
    qa_agent -->|writing issues| writer
    finalize --> END

    style collector fill:#4CAF50,color:#fff
    style analyst fill:#2196F3,color:#fff
    style writer fill:#FF9800,color:#fff
    style qa_agent fill:#F44336,color:#fff
    style finalize fill:#9C27B0,color:#fff""")


def main():
    parser = argparse.ArgumentParser(
        prog="competitive-analysis",
        description="AI-Driven Competitive Analysis Agent System",
    )
    parser.add_argument("--env", default=None, help="Path to .env file")
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Run competitive analysis")
    p_analyze.add_argument("query", help="Analysis query")
    p_analyze.add_argument("--competitors", nargs="+", default=[])
    p_analyze.add_argument("--format", choices=["markdown", "html"], default="markdown")

    # eval
    p_eval = subparsers.add_parser("eval", help="Run evaluation scenario")
    p_eval.add_argument("--scenario", default="all")

    # trace
    p_trace = subparsers.add_parser("trace", help="View run trace")
    p_trace.add_argument("--run-id", required=True)
    p_trace.add_argument("--events", action="store_true")

    # visualize
    subparsers.add_parser("visualize", help="Print workflow DAG")

    # interactive
    subparsers.add_parser("interactive", help="Launch interactive menu (default)")

    args = parser.parse_args()

    # Default: no subcommand -> launch interactive mode
    if not args.command or args.command == "interactive":
        from .interactive import run_interactive
        run_interactive(env_path=args.env, log_level=args.log_level or "WARNING")
        return

    from ..utils.config import load_config
    from ..utils.logger import setup_logger

    config = load_config(args.env)
    setup_logger(level=args.log_level or config.log_level)

    if args.command == "analyze":
        cmd_analyze(args, config)
    elif args.command == "eval":
        cmd_eval(args, config)
    elif args.command == "trace":
        cmd_trace(args, config)
    elif args.command == "visualize":
        cmd_visualize(args, config)


if __name__ == "__main__":
    main()
