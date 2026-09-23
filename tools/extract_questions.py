from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf


GREEN = 0x28A745
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SECTION_NAMES = {
    "FA 1 ProgTools": "FA1",
    "FA 2 ProgTools": "FA2",
}


def clean(spans: list[dict]) -> str:
    value = "".join(span["text"] for span in spans)
    value = value.replace("●\u200b", "").replace("●", "")
    value = value.replace("✓", "").replace("✗", "")
    return re.sub(r"\s+", " ", value).strip()


def extract(pdf_path: Path) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    assessment = ""
    questions: list[dict] = []
    counts = {"FA1": 0, "FA2": 0}
    prompt_parts: list[str] = []
    options: list[dict] = []
    active_option: dict | None = None
    in_options = False

    def finish_option() -> None:
        nonlocal active_option
        if active_option is None:
            return
        active_option["text"] = re.sub(
            r"\s+", " ", " ".join(active_option.pop("parts"))
        ).strip()
        options.append(active_option)
        active_option = None

    def finish_question() -> None:
        nonlocal prompt_parts, options, active_option, in_options
        finish_option()
        text = re.sub(r"\s+", " ", " ".join(prompt_parts)).strip()
        if assessment and text and options:
            counts[assessment] += 1
            number = counts[assessment]
            answers = [
                LETTERS[index]
                for index, option in enumerate(options)
                if option["correct"]
            ]
            questions.append(
                {
                    "id": f"progtools-{assessment.lower()}-{number}",
                    "number": number,
                    "globalNumber": len(questions) + 1,
                    "assessment": assessment,
                    "category": (
                        "FA1: Coding Standards and Development Tools"
                        if assessment == "FA1"
                        else "FA2: IDEs, VS Code Extensions, and Debugging"
                    ),
                    "type": "choice",
                    "text": text,
                    "options": [option["text"] for option in options],
                    "answer": answers,
                }
            )
        prompt_parts = []
        options = []
        active_option = None
        in_options = False

    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line["spans"]
                raw = "".join(span["text"] for span in spans)
                stripped = raw.strip()

                if stripped in SECTION_NAMES:
                    finish_question()
                    assessment = SECTION_NAMES[stripped]
                    continue
                if not assessment or stripped.startswith("Score:"):
                    continue

                text = clean(spans)
                is_bullet = "●" in raw
                is_blank = not stripped
                is_marker_only = not text and ("✓" in raw or "✗" in raw)
                is_correct = any(span["color"] == GREEN for span in spans)

                if is_blank:
                    if in_options:
                        finish_question()
                    continue
                if is_marker_only:
                    continue
                if is_bullet:
                    finish_option()
                    in_options = True
                    active_option = {
                        "parts": [text] if text else [],
                        "correct": is_correct,
                    }
                    continue
                if in_options and active_option is not None:
                    active_option["parts"].append(text)
                    active_option["correct"] = active_option["correct"] or is_correct
                elif text:
                    prompt_parts.append(text)

    finish_question()
    return questions


def main() -> None:
    pdf_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    questions = extract(pdf_path)
    counts = {
        assessment: sum(question["assessment"] == assessment for question in questions)
        for assessment in ("FA1", "FA2")
    }
    errors = []
    if counts != {"FA1": 18, "FA2": 13}:
        errors.append(f"unexpected assessment counts: {counts}")
    for question in questions:
        if len(question["options"]) < 2:
            errors.append(f"{question['id']} has fewer than two options")
        if len(question["answer"]) != 1:
            errors.append(f"{question['id']} should have one correct answer")
    if errors:
        raise ValueError("; ".join(errors))

    output_dir.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(questions, ensure_ascii=False, indent=2)
    (output_dir / "questions.json").write_text(json_text + "\n", encoding="utf-8")
    (output_dir / "questions.js").write_text(
        "window.PROGTOOLS_QUESTIONS = " + json_text + ";\n", encoding="utf-8"
    )
    print(f"Extracted {len(questions)} questions: {counts}")


if __name__ == "__main__":
    main()
