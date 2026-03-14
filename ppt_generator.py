from pptx import Presentation
import os
import uuid

TEMPLATE_DIR = "templates"

def parse_slides(text):
    slides = []
    title = None
    content = []

    for line in text.split("\n"):
        if line.startswith("SLIDE:"):
            if title:
                slides.append((title, "\n".join(content)))
            title = line.replace("SLIDE:", "").strip()
            content = []
        else:
            content.append(line)
    if title:
        slides.append((title, "\n".join(content)))
    return slides


def generate_presentation(topic, lesson_text, template_name):
    template_path = os.path.join(TEMPLATE_DIR, template_name)
    prs = Presentation(template_path)
    slides = parse_slides(lesson_text)

    for title, content in slides:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        slide.placeholders[1].text = content

    os.makedirs("generated", exist_ok=True)
    file_name = f"{topic}_{uuid.uuid4().hex[:5]}.pptx"
    path = os.path.join("generated", file_name)
    prs.save(path)
    return path