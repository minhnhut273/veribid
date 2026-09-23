from __future__ import annotations

import base64
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "submission" / "assets"
SOURCE = ROOT / "Document" / "Phase_1" / "Diagram" / "System_architecture" / "VeriBid_AWS_System_Architecture_v0.1.drawio"
ICON_ROOT = Path.home() / "AppData" / "Local" / "Temp" / "veribid-aws-architecture-icons"

ICON_PATHS = {
    "amplify": "Architecture-Service-Icons_02072025/Arch_Front-End-Web-Mobile/64/Arch_AWS-Amplify_64.png",
    "cognito": "Architecture-Service-Icons_02072025/Arch_Security-Identity-Compliance/64/Arch_Amazon-Cognito_64.png",
    "api_gateway": "Architecture-Service-Icons_02072025/Arch_Networking-Content-Delivery/64/Arch_Amazon-API-Gateway_64.png",
    "lambda": "Architecture-Service-Icons_02072025/Arch_Compute/64/Arch_AWS-Lambda_64.png",
    "step_functions": "Architecture-Service-Icons_02072025/Arch_App-Integration/64/Arch_AWS-Step-Functions_64.png",
    "s3": "Architecture-Service-Icons_02072025/Arch_Storage/64/Arch_Amazon-Simple-Storage-Service_64.png",
    "dynamodb": "Architecture-Service-Icons_02072025/Arch_Database/64/Arch_Amazon-DynamoDB_64.png",
    "bedrock": "Architecture-Service-Icons_02072025/Arch_Artificial-Intelligence/64/Arch_Amazon-Bedrock_64.png",
    "cloudwatch": "Architecture-Service-Icons_02072025/Arch_Management-Governance/64/Arch_Amazon-CloudWatch_64.png",
    "identity_and_access_management": "Architecture-Service-Icons_02072025/Arch_Security-Identity-Compliance/64/Arch_AWS-Identity-and-Access-Management_64.png",
    "textract": "Architecture-Service-Icons_02072025/Arch_Artificial-Intelligence/64/Arch_Amazon-Textract_64.png",
}


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def style_map(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in style.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def clean_lines(value: str) -> list[str]:
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return [line.strip() for line in value.splitlines() if line.strip()]


def icon_data(res_icon: str) -> str | None:
    key = res_icon.removeprefix("mxgraph.aws4.")
    relative = ICON_PATHS.get(key)
    if not relative:
        return None
    path = ICON_ROOT / relative
    if not path.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def geometry(cell: ET.Element) -> tuple[float, float, float, float]:
    g = cell.find("mxGeometry")
    if g is None:
        return 0, 0, 0, 0
    return tuple(float(g.get(name, 0)) for name in ("x", "y", "width", "height"))  # type: ignore[return-value]


def edge_points(cell: ET.Element) -> list[tuple[float, float]]:
    g = cell.find("mxGeometry")
    if g is None:
        return []
    array = g.find("Array")
    if array is None:
        return []
    return [(float(p.get("x", 0)), float(p.get("y", 0))) for p in array.findall("mxPoint")]


def port(cell: ET.Element, kind: str, default_x: float, default_y: float) -> tuple[float, float]:
    x, y, w, h = geometry(cell)
    s = style_map(cell.get("style", ""))
    px = float(s.get(f"{kind}X", default_x))
    py = float(s.get(f"{kind}Y", default_y))
    return x + w * px, y + h * py


def render_text(cell: ET.Element) -> str:
    x, y, w, h = geometry(cell)
    s = style_map(cell.get("style", ""))
    lines = clean_lines(cell.get("value", ""))
    if not lines:
        return ""
    fill = s.get("fillColor", "none")
    stroke = s.get("strokeColor", "none")
    radius = 8 if s.get("rounded") == "1" else 0
    out = []
    if fill != "none":
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    align = s.get("align", "center")
    anchor = {"left": "start", "right": "end", "center": "middle"}.get(align, "middle")
    tx = x + (12 if anchor == "start" else w - 12 if anchor == "end" else w / 2)
    font_size = int(s.get("fontSize", "12"))
    weight = "700" if s.get("fontStyle") == "1" else "400"
    color = s.get("fontColor", "#334155")
    line_height = font_size + 4
    first_y = y + max(font_size + 4, (h - line_height * len(lines)) / 2 + font_size)
    for i, line in enumerate(lines):
        out.append(f'<text x="{tx:g}" y="{first_y + i * line_height:g}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{font_size}px" font-weight="{weight}" fill="{color}">{esc(line)}</text>')
    return "".join(out)


def main() -> None:
    tree = ET.parse(SOURCE)
    graph = tree.getroot().find("diagram/mxGraphModel/root")
    if graph is None:
        raise RuntimeError(f"No graph root in {SOURCE}")
    cells = {cell.get("id"): cell for cell in graph.findall("mxCell") if cell.get("id")}
    nodes = [cell for cell in cells.values() if cell.get("vertex") == "1"]
    edges = [cell for cell in cells.values() if cell.get("edge") == "1"]
    out = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1000" viewBox="0 0 1800 1000">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
<rect width="1800" height="1000" fill="#ffffff"/>''']

    for cell in nodes:
        cid = cell.get("id", "")
        if cid == "awscloud":
            x, y, w, h = geometry(cell)
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="12" fill="#ffffff" stroke="#879196" stroke-width="2"/>')
            out.append(f'<text x="{x + 44:g}" y="{y + 28:g}" font-family="Arial,sans-serif" font-size="14px" font-weight="700" fill="#232F3E">AWS Cloud — VeriBid Production</text>')
        elif cid.startswith("lane_"):
            x, y, w, h = geometry(cell)
            fill = style_map(cell.get("style", "")).get("fillColor", "#f8fafc")
            out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="{fill}" stroke="#cbd5e1" stroke-width="1.5"/>')
            lines = clean_lines(cell.get("value", ""))
            if lines:
                out.append(f'<text x="{x + 14:g}" y="{y + 22:g}" font-family="Arial,sans-serif" font-size="11px" font-weight="700" fill="#4b5563">{esc(lines[0])}</text>')

    for cell in edges:
        source = cells.get(cell.get("source"))
        target = cells.get(cell.get("target"))
        if source is None or target is None:
            continue
        points = [port(source, "exit", 1, 0.5), *edge_points(cell), port(target, "entry", 0, 0.5)]
        d = " ".join(("M" if i == 0 else "L") + f"{x:g},{y:g}" for i, (x, y) in enumerate(points))
        s = style_map(cell.get("style", ""))
        dash = ' stroke-dasharray="6 5"' if s.get("dashed") == "1" else ""
        out.append(f'<path d="{d}" fill="none" stroke="{s.get("strokeColor", "#64748b")}" stroke-width="{s.get("strokeWidth", "1.5")}"{dash} marker-end="url(#arrow)"/>')
        label = clean_lines(cell.get("value", ""))
        if label:
            label[0] = {
                "Role / policy controls API + workflow": "IAM policy",
                "StartExecution • 202": "StartExecution / 202",
                "Read source objects": "Read source",
                "Generate report": "Generate export",
                "Write Markdown / PDF": "Write export",
                "Runtime telemetry": "Telemetry",
                "Conditional OCR (not deployed)": "Conditional OCR",
            }.get(label[0], label[0])
            mx, my = points[len(points) // 2]
            label_width = max(28, len(label[0]) * 5.8 + 10)
            out.append(f'<rect x="{mx - label_width / 2:g}" y="{my - 18:g}" width="{label_width:g}" height="14" rx="3" fill="#ffffff" opacity="0.92"/>')
            out.append(f'<text x="{mx:g}" y="{my - 7:g}" text-anchor="middle" font-family="Arial,sans-serif" font-size="10px" fill="#475569">{esc(label[0])}</text>')

    for cell in nodes:
        cid = cell.get("id", "")
        if cid in {"0", "1", "awscloud"} or cid.startswith("lane_"):
            continue
        x, y, w, h = geometry(cell)
        s = style_map(cell.get("style", ""))
        if s.get("resIcon", "").endswith(".user") or s.get("shape", "").endswith(".user"):
            cx = x + w / 2
            out.append(f'<circle cx="{cx:g}" cy="{y + 22:g}" r="14" fill="#232F3E"/>')
            out.append(f'<path d="M{x + 12:g},{y + 58:g} Q{cx:g},{y + 34:g} {x + w - 12:g},{y + 58:g} L{x + w - 12:g},{y + 70:g} L{x + 12:g},{y + 70:g} Z" fill="#232F3E"/>')
            continue
        data = icon_data(s.get("resIcon", ""))
        if data:
            size = min(w, h, 82)
            out.append(f'<image href="{data}" x="{x + (w - size) / 2:g}" y="{y + 4:g}" width="{size:g}" height="{size:g}"/>')
        else:
            out.append(render_text(cell))

    out.append('<text x="215" y="955" font-family="Arial,sans-serif" font-size="10px" fill="#475569">Solid = request/data/control flow   Dashed = upload, observability or conditional path   AgentCore and dedicated vector DB are excluded.</text>')
    out.append("</svg>")
    path = ASSETS / "aws_architecture_official.svg"
    path.write_text("\n".join(out), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
