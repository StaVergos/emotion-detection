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

export type VideoItem = {
    id: string
    audio_object: string
    created_at: string
    emotion_prompt_result: string
    emotions: Emotions[]
    transcript: string
    transcript_process_status: "uploaded" | "processing" | "completed"
    video_filename: string
    video_object: string
}

export type VideoItemRaw = Omit<VideoItem, "id"> & {
    _id: string
}

export type VideoColumn = {
    id: string
    video_filename: string
    transcript_process_status: "uploaded" | "processing" | "completed"
    created_at: string
}