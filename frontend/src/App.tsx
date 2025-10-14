import { useState, useEffect, useCallback, useRef } from "react"
import { AddVideo } from "./components/videos/addVideo"
import VideoTablePage from "./components/videos/page"
import type { VideoItem, OpenAIAnalysis } from "./types"
import { TranscriptDialog } from "./components/videos/transcriptDialog"
import { OpenAIDialog } from "./components/videos/openAIDialog"

function App() {
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)

  const [openAIAnalysis, setOpenAIAnalysis] = useState<OpenAIAnalysis[]>([])
  const [openAILoading, setOpenAILoading] = useState(false)
  const [openAIError, setOpenAIError] = useState<string | null>(null)

  const [errorMessage, setError] = useState<string | null>(null)
  const [dialogTranscriptOpen, setDialogTranscriptOpen] = useState(false)
  const [dialogOpenAIAnalysisOpen, setDialogOpenAIAnalysisOpen] = useState(false)
  const [currentTranscript, setCurrentTranscript] = useState("")
  const currentOpenAIAnalysis = useRef<OpenAIAnalysis | null>(null)

  const fetchVideos = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("http://localhost:8000/videos")
      if (res.status === 404) {
        setVideos([])
        return
      }
      const json = await res.json()
      if (!res.ok) throw new Error((json.detail as string) || `Error ${res.status}`)

      const normalized = json.videos.map((r: any) => ({
        _id: r._id,
        id: r._id.slice(-5),
        audio_object: r.audio_object_path,
        created_at: new Date(r.created_at)
          .toISOString()
          .split("T")
          .join(" ")
          .split(".")[0],
        emotion_prompt_result: r.emotion_prompt_result,
        emotions: r.emotion_chunks,
        transcript: r.transcription_result,
        processing_status: r.processing_status,
        video_filename: r.video_filename,
        video_object: r.video_object_path,
        evaluation_metrics: r.evaluation_metrics ?? null,
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

  useEffect(() => {
    if (videos.length === 0) {
      setOpenAIAnalysis([])
      setOpenAILoading(false)
      setOpenAIError(null)
      return
    }

    const doAnalysis = async () => {
      setOpenAILoading(true)
      setOpenAIError(null)
      setOpenAIAnalysis([])

      try {
        const results = await Promise.all(
          videos.map(async (v) => {
            const res = await fetch(
              `http://localhost:8000/videos/${v._id}/openai`,
              {
                method: "GET",
                headers: {
                  "Content-Type": "application/json",
                },
              }
            )
            if (!res.ok) throw new Error(`Error ${res.status}`)
            const json = await res.json()
            return {
              video_id: v._id,
              prompt: json.prompt,
              analysis: json.analysis,
            } as OpenAIAnalysis
          })
        )
        setOpenAIAnalysis(results)
      } catch (err: any) {
        console.error("OpenAI analysis error:", err)
        setOpenAIError(err.message)
      } finally {
        setOpenAILoading(false)
      }
    }

    doAnalysis()
  }, [videos])

  const handleUploadSuccess = useCallback(() => {
    fetchVideos()
  }, [fetchVideos])

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

  const handleViewTranscript = useCallback(
    (videoId: string) => {
      const vid = videos.find((v) => v._id === videoId)
      if (vid && vid.transcript) {
        setCurrentTranscript(vid.transcript)
        setDialogTranscriptOpen(true)
      }
    },
    [videos]
  )
  const handleViewOpenAIAnalysis = useCallback((videoID: string) => {
    const analysis: OpenAIAnalysis | undefined = openAIAnalysis.find((a) => a.video_id === videoID)
    if (analysis) {
      currentOpenAIAnalysis.current = analysis
      setDialogOpenAIAnalysisOpen(true)
    }
  }, [openAIAnalysis])

  return (
    <div className="rounded-lg h-full min-h-auto bg-slate-100">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8">
        <div className="rounded-lg bg-white p-6 shadow-lg">
          <h1 className="text-3xl font-bold text-slate-900 lg:text-4xl">Emotion Detection</h1>
        </div>

        <div className="rounded-lg bg-white p-6 shadow-lg">
          <AddVideo onUploadSuccess={handleUploadSuccess} />
        </div>

        <div className="rounded-lg bg-white p-6 shadow-lg">
          <VideoTablePage
            loading={loading}
            error={errorMessage}
            data={videos}
            onDelete={handleDelete}
            onViewTranscript={handleViewTranscript}
            onViewOpenAIAnalysis={handleViewOpenAIAnalysis}
          />
        </div>

        <TranscriptDialog
          open={dialogTranscriptOpen}
          transcript={currentTranscript}
          onClose={() => setDialogTranscriptOpen(false)}
        />

        <OpenAIDialog
          open={dialogOpenAIAnalysisOpen}
          prompt={currentOpenAIAnalysis.current?.prompt ?? []}
          analysis={currentOpenAIAnalysis.current?.analysis ?? ""}
          onClose={() => setDialogOpenAIAnalysisOpen(false)}
        />
      </div>
    </div>
  )
}

export default App
