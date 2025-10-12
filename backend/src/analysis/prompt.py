from src.api.schemas import EmotionSegment
from src.api.constants import FACE_PROBABILITY_FIELDS


def build_condition_messages(chunks: list[EmotionSegment]) -> list[dict[str, str]]:
    system_content = (
        "You are a clinical psychologist. Below is a multimodal breakdown of a speaker.\n"
        "Please summarize their overall emotional and psychological condition and follow the response format precisely."
    )

    lines = ["Timeline:"]
    for seg in chunks:
        start, end = seg.timestamp
        ts = f"{int(start // 60):02d}:{int(start % 60):02d}-{int(end // 60):02d}:{int(end % 60):02d}"
        te = f"{seg.emotion} ({seg.emotion_score:.2f})"
        vad = seg.vad_score
        va = f"A{vad.arousal:.2f}/V{vad.valence:.2f}/D{vad.dominance:.2f}"
        fe = seg.face_emotions
        if fe is None or all(
            getattr(fe, attr) is None for attr in type(fe).model_fields
        ):
            face_str = "No face detected"
        else:
            prob_parts = []
            for field in FACE_PROBABILITY_FIELDS:
                value = getattr(fe, field)
                if value is not None:
                    prob_parts.append(f"{field}:{value:.2f}")

            transition_parts = []
            if fe.initial_emotion and fe.final_emotion:
                transition_parts.append(
                    f"Init→Final:{fe.initial_emotion}→{fe.final_emotion}"
                )
            elif fe.initial_emotion:
                transition_parts.append(f"Initial:{fe.initial_emotion}")
            if fe.dominant_emotion:
                transition_parts.append(f"Dominant:{fe.dominant_emotion}")
            if fe.emotion_stability:
                transition_parts.append(f"Stability:{fe.emotion_stability}")

            sections = []
            if prob_parts:
                sections.append("Probs(" + ", ".join(prob_parts) + ")")
            if transition_parts:
                sections.append("Meta(" + "; ".join(transition_parts) + ")")
            face_str = " ".join(sections) if sections else "No face detected"
        text = seg.text.strip()
        lines.append(
            f"[{ts}] Text: {text}  Text‐emo: {te}  Audio(VAD): {va}  Face: {face_str}"
        )

    lines.append("\nRespond with a JSON object containing the following keys:")
    lines.append(
        "- overall_summary: concise synthesis of the speaker's emotional state and shifts."
    )
    lines.append(
        "- most_informative_modality: explain which modality (text, audio, face) provided the clearest insight and why."
    )
    lines.append(
        "- modality_conflicts: note any disagreements between modalities and how you resolved them (use 'none' if there were no conflicts)."
    )
    lines.append(
        "- confidence: rate your confidence as low/medium/high with a short rationale grounded in the data."
    )
    user_content = "\n".join(lines)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
