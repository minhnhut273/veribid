from __future__ import annotations

import base64
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "submission" / "assets"
ICON_ROOT = Path.home() / "AppData" / "Local" / "Temp" / "veribid-aws-architecture-icons"


ICONS = {
    "amplify": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Front-End-Web-Mobile" / "64" / "Arch_AWS-Amplify_64.png",
    "cognito": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Security-Identity-Compliance" / "64" / "Arch_Amazon-Cognito_64.png",
    "api": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Networking-Content-Delivery" / "64" / "Arch_Amazon-API-Gateway_64.png",
    "lambda": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Compute" / "64" / "Arch_AWS-Lambda_64.png",
    "step": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_App-Integration" / "64" / "Arch_AWS-Step-Functions_64.png",
    "s3": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Storage" / "64" / "Arch_Amazon-Simple-Storage-Service_64.png",
    "ddb": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Database" / "64" / "Arch_Amazon-DynamoDB_64.png",
    "bedrock": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Artificial-Intelligence" / "64" / "Arch_Amazon-Bedrock_64.png",
    "watch": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Management-Governance" / "64" / "Arch_Amazon-CloudWatch_64.png",
    "iam": ICON_ROOT / "Architecture-Service-Icons_02072025" / "Arch_Security-Identity-Compliance" / "64" / "Arch_AWS-Identity-and-Access-Management_64.png",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def icon_data(name: str) -> str:
    path = ICONS[name]
    if not path.exists():
        raise FileNotFoundError(path)
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def node(x: int, y: int, icon: str, title: str, subtitle: str, tone: str = "orange") -> str:
    colors = {
        "orange": ("#fff7ed", "#f97316"),
        "purple": ("#faf5ff", "#8b5cf6"),
        "pink": ("#fdf2f8", "#db2777"),
        "green": ("#f0fdf4", "#16a34a"),
        "teal": ("#ecfeff", "#0f766e"),
        "blue": ("#eff6ff", "#2563eb"),
        "slate": ("#f8fafc", "#475569"),
    }
    fill, stroke = colors[tone]
    return f'''<g transform="translate({x},{y})">
  <rect x="0" y="0" width="220" height="176" rx="18" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
  <image href="{icon_data(icon)}" x="78" y="14" width="64" height="64"/>
  <text x="110" y="104" text-anchor="middle" class="service">{esc(title)}</text>
  <text x="110" y="130" text-anchor="middle" class="detail">{esc(subtitle)}</text>
</g>'''


def human_node(x: int, y: int, title: str, subtitle: str) -> str:
    return f'''<g transform="translate({x},{y})">
  <rect x="0" y="0" width="220" height="176" rx="18" fill="#f8fafc" stroke="#475569" stroke-width="2"/>
  <circle cx="110" cy="42" r="18" fill="#475569"/>
  <path d="M76 76 Q110 52 144 76 L144 88 L76 88 Z" fill="#475569"/>
  <text x="110" y="116" text-anchor="middle" class="service">{esc(title)}</text>
  <text x="110" y="142" text-anchor="middle" class="detail">{esc(subtitle)}</text>
</g>'''


def arrow(x1: int, y1: int, x2: int, y2: int, label: str = "", dashed: bool = False) -> str:
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    label_svg = ""
    if label:
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2 - 8
        label_svg = f'<text x="{mx}" y="{my}" text-anchor="middle" class="edge-label">{esc(label)}</text>'
    return f'<path d="M{x1},{y1} L{x2},{y2}" class="edge"{dash} marker-end="url(#arrow)"/>{label_svg}'


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="1040" viewBox="0 0 1600 1040">
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker>
  <style>
    .title {{ font: 700 34px Arial, sans-serif; fill: #0f172a; }}
    .subtitle {{ font: 18px Arial, sans-serif; fill: #475569; }}
    .tier {{ font: 700 16px Arial, sans-serif; fill: #334155; }}
    .service {{ font: 700 16px Arial, sans-serif; fill: #1e293b; }}
    .detail {{ font: 14px Arial, sans-serif; fill: #475569; }}
    .edge {{ fill: none; stroke: #64748b; stroke-width: 3; }}
    .edge-label {{ font: 12px Arial, sans-serif; fill: #475569; paint-order: stroke; stroke: #f8fafc; stroke-width: 5px; }}
    .note {{ font: 14px Arial, sans-serif; fill: #475569; }}
    .small {{ font: 12px Arial, sans-serif; fill: #64748b; }}
  </style>
</defs>
<rect width="1600" height="1040" fill="#f8fafc"/>
<text x="70" y="58" class="title">VeriBid — AWS System Architecture</text>
<text x="70" y="88" class="subtitle">Evidence-grounded asynchronous evaluation with human final authority</text>
<rect x="45" y="118" width="1510" height="820" rx="24" fill="#ffffff" stroke="#94a3b8" stroke-width="2" stroke-dasharray="10 7"/>
<text x="75" y="153" class="tier">AWS Cloud • VeriBid MVP baseline</text>

<rect x="75" y="180" width="1450" height="205" rx="18" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="100" y="212" class="tier">ACCESS &amp; ASYNC CONTROL PLANE</text>
{node(105, 225, "amplify", "AWS Amplify", "React frontend", "purple")}
{node(365, 225, "cognito", "Amazon Cognito", "JWT identity", "pink")}
{node(625, 225, "api", "Amazon API Gateway", "/api/v1 boundary", "pink")}
{node(885, 225, "lambda", "AWS Lambda", "API handler", "orange")}
{node(1145, 225, "step", "AWS Step Functions", "async workflow", "pink")}

<rect x="75" y="415" width="1450" height="250" rx="18" fill="#ffffff" stroke="#cbd5e1"/>
<text x="100" y="447" class="tier">EVIDENCE, SEMANTIC + DETERMINISTIC EVALUATION PATHS</text>
{node(145, 475, "s3", "Amazon S3", "source docs + artifacts", "orange")}
{node(465, 475, "bedrock", "Amazon Bedrock", "evaluators + verifier", "teal")}
{node(785, 475, "lambda", "AWS Lambda", "rules / TCO / scoring", "orange")}
{node(1105, 475, "ddb", "Amazon DynamoDB", "domain state + audit", "blue")}

<rect x="75" y="695" width="1450" height="205" rx="18" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="100" y="727" class="tier">HUMAN REVIEW, EXPORT &amp; OBSERVABILITY</text>
{human_node(375, 750, "Human Review", "final authority")}
{node(695, 750, "lambda", "AWS Lambda", "defensible export", "orange")}
{node(1015, 750, "watch", "Amazon CloudWatch", "logs + metrics", "green")}

{arrow(325, 313, 365, 313, "sign in")}
{arrow(585, 313, 625, 313, "REST")}
{arrow(845, 313, 885, 313, "invoke")}
{arrow(1105, 313, 1145, 313, "start execution")}
{arrow(475, 401, 255, 475, "upload", True)}
{arrow(1255, 401, 255, 475, "read / persist")}
{arrow(1255, 401, 465, 475, "semantic")}
{arrow(1255, 401, 785, 475, "deterministic")}
{arrow(1255, 401, 1215, 475, "state")}
{arrow(575, 651, 485, 750, "review")}
{arrow(895, 651, 805, 750, "export")}
{arrow(1215, 651, 1125, 750, "telemetry", True)}
{arrow(1225, 651, 1215, 651, "", True)}

<rect x="75" y="958" width="1450" height="48" rx="12" fill="#eef2ff" stroke="#c7d2fe"/>
<text x="95" y="988" class="note">MVP boundary: Amplify, Cognito, API Gateway, Lambda, Step Functions, Bedrock, S3, DynamoDB and CloudWatch. Human review remains the final decision authority.</text>
<text x="1525" y="1028" text-anchor="end" class="small">AWS Architecture Icons used for service nodes • explanatory diagram, not an AWS Console screenshot</text>
</svg>'''
    svg_path = ASSETS / "aws_architecture_official.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(svg_path)


if __name__ == "__main__":
    main()
