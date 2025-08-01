from src.api.schemas import EmotionSegment


def build_condition_messages(chunks: list[EmotionSegment]) -> list[dict[str, str]]:
    system_content = (
        "You are a clinical psychologist. Below is a multimodal breakdown of a speaker.\n"
        "Please summarize their overall emotional and psychological condition."
    )

    lines = ["Timeline:"]
    for seg in chunks:
        start, end = seg.timestamp
        ts = f"{int(start // 60):02d}:{int(start % 60):02d}-{int(end // 60):02d}:{int(end % 60):02d}"
        te = f"{seg.emotion} ({seg.emotion_score:.2f})"
        vad = seg.vad_score
        va = f"A{vad.arousal:.2f}/V{vad.valence:.2f}/D{vad.dominance:.2f}"
        fe = seg.face_emotions
        face_str = ", ".join(f"{k}:{getattr(fe, k):.2f}" for k in type(fe).model_fields)
        text = seg.text.strip()
        lines.append(
            f"[{ts}] Text: {text}  Text‐emo: {te}  Audio(VAD): {va}  Face: {face_str}"
        )

    lines.append("\nAnswer in a few paragraphs:")
    user_content = "\n".join(lines)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
