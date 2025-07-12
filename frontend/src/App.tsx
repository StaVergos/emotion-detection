import { useState, useEffect, useCallback, useRef } from "react"
import { AddVideo } from "./components/videos/addVideo"
import VideoTablePage from "./components/videos/page"
import type { VideoItem, ProcessingStatus } from "./types"

function App() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMessage, setError] = useState<string | null>(null)

  const [processingStatus, setProcessingStatus] = useState<
    Record<string, ProcessingStatus>
  >({})
  const wsRefs = useRef<Record<string, WebSocket>>({})

  const fetchVideos = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/videos")

      // empty list is fine
      if (res.status === 404) {
        setVideos([])
        return
      }

      const json = await res.json()
      if (!res.ok) {
        const detail =
          typeof json === "object" && "detail" in json
            ? (json.detail as string)
            : `Error ${res.status}`
        throw new Error(detail)
      }

      const normalized: VideoItem[] = json.videos.map((raw: any) => ({
        _id: raw._id,
        id: raw._id.slice(-5),
        audio_object: raw.audio_object_path,
        created_at: new Date(raw.created_at)
          .toISOString()
          .replace("T", " ")
          .split(".")[0],
        emotion_prompt_result: raw.emotion_prompt_result,
        emotions: raw.emotion_chunks,
        transcript: raw.transcription_result,
        processing_status: raw.processing_status,
        video_filename: raw.video_filename,
        video_object: raw.video_object_path,
      }))
      setVideos(normalized)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchVideos()
  }, [fetchVideos])

  const listenToJob = useCallback(
    (videoId: string, initialStatus: ProcessingStatus) => {
      setProcessingStatus((ps) => ({ ...ps, [videoId]: initialStatus }))
      const ws = new WebSocket(`ws://localhost:8000/ws/status/${videoId}`)
      wsRefs.current[videoId] = ws

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data) as { step: ProcessingStatus;[k: string]: any }
        setProcessingStatus((ps) => ({
          ...ps,
          [videoId]: msg.step,
        }))

        if (msg.step === "audio_chunked") {
          ws.close()
          setProcessingStatus((ps) => {
            const next = { ...ps }
            delete next[videoId]
            return next
          })
          fetchVideos()
        }
      }

      ws.onerror = () => {
        ws.close()
        setProcessingStatus((ps) => {
          const next = { ...ps }
          delete next[videoId]
          return next
        })
      }
    },
    [fetchVideos]
  )

  const handleUploadSuccess = useCallback(
    (videoId: string) => {
      // start listening to the video_id channel
      listenToJob(videoId, "video_uploaded")
      fetchVideos()
    },
    [listenToJob, fetchVideos]
  )

  const handleDelete = useCallback(
    async (rawId: string) => {
      try {
        const res = await fetch(`http://localhost:8000/videos/${rawId}`, {
          method: "DELETE",
        })
        if (res.status === 204) {
          await fetchVideos()
        } else {
          const json = await res.json().catch(() => ({}))
          throw new Error(json.detail ?? `Delete failed (${res.status})`)
        }
      } catch (err: any) {
        alert(`Could not delete video: ${err.message}`)
      }
    },
    [fetchVideos]
  )

  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach((ws) => ws.close())
    }
  }, [])

  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-xl w-full text-center space-y-6">
        <h1 className="text-2xl font-bold">Emotion Detection</h1>

        <AddVideo onUploadSuccess={handleUploadSuccess} />

        <VideoTablePage
          loading={loading}
          error={errorMessage}
          data={videos}
          processingStatus={processingStatus}
          onDelete={handleDelete}
        />
      </div>
    </div>
  )
}

export default App
