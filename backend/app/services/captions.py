from app.schemas import CaptionOptions

ALIGNMENT = {"bottom": 2, "middle": 5, "top": 8}


def ass_color(hex_color, tag=False):
    """#RRGGBB -> ASS colour (&H00BBGGRR for styles, &HBBGGRR& for inline tags)."""
    r, g, b = hex_color[1:3], hex_color[3:5], hex_color[5:7]
    bgr = f"{b}{g}{r}".upper()
    return f"&H{bgr}&" if tag else f"&H00{bgr}"


def ass_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def clean_text(text, options):
    # Braces would be read as ASS override tags
    text = " ".join(text.split()).replace("{", "(").replace("}", ")")
    return text.upper() if options.uppercase else text


def split_segments(segments, max_words):
    """Break Whisper segments into captions of at most max_words words."""
    captions = []
    for segment in segments:
        words = segment.get("words")
        if words:
            timed = [(w["word"], w["start"], w["end"]) for w in words if w["word"].strip()]
        else:
            # No word timestamps: spread the words evenly over the segment
            tokens = segment["text"].split()
            if not tokens:
                continue
            step = (segment["end"] - segment["start"]) / len(tokens)
            timed = [
                (token, segment["start"] + i * step, segment["start"] + (i + 1) * step)
                for i, token in enumerate(tokens)
            ]

        for i in range(0, len(timed), max_words):
            chunk = timed[i:i + max_words]
            captions.append({
                "start": chunk[0][1],
                "end": chunk[-1][2],
                "text": " ".join(word.strip() for word, _, _ in chunk),
            })
    return captions


def build_ass(segments, options: CaptionOptions):
    """Render Whisper segments as an .ASS subtitle file."""
    if options.max_words:
        segments = split_segments(segments, options.max_words)

    if options.background:
        border_style, outline_colour = 3, ass_color(options.background_color)
    else:
        border_style, outline_colour = 1, ass_color(options.outline_color)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",  # No wrapping
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{options.font_name},{options.font_size},&H00FFFFFF,{outline_colour},&H00000000,"
        f"{-1 if options.bold else 0},{-1 if options.italic else 0},0,0,100,100,0,0,"
        f"{border_style},{options.outline_width:g},{options.shadow:g},{ALIGNMENT[options.position]},"
        f"30,30,{options.margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    if segments:
        for idx, segment in enumerate(segments):
            color = ass_color(options.colors[idx % len(options.colors)], tag=True)
            color_tag = f"{{\\c{color}}}"
            lines.append(
                f"Dialogue: 0,{ass_timestamp(segment['start'])},{ass_timestamp(segment['end'])},"
                f"Default,,0,0,0,,{color_tag}{clean_text(segment['text'], options)}"
            )
    else:
        lines.append("Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,No speech detected")

    return "\n".join(lines) + "\n"
