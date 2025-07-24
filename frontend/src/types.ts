// remove extract_job_id entirely
export type APIError = {
    code: number
    message: string
    source: string
}

export type Emotions = {
    emotion: string
    emotion_score: number
    text: string
    timestamp: [number, number]
}

export type ProcessingStatus =
    | "video_uploaded"
    | "audio_extracted"
    | "transcription_completed"
    | "transcription_chunks_emotion_completed"
    | "audio_chunks_uploaded"
    | "audio_chunks_emotion_completed"
    | "video_face_recognizion"
    | "video_face_recognizion_emotion"

export type VideoItem = {
    _id: string
    id?: string
    audio_object: string
    created_at: string
    emotion_prompt_result: string
    emotions: Emotions[]
    transcript: string
    processing_status: ProcessingStatus
    video_filename: string
    video_object: string
}


export type VideoColumn = {
    id: string
    video_filename: string
    processing_status: "uploading" | "uploaded" | "processing" | "completed"
    created_at: string
}