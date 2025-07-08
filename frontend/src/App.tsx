import { useState, useEffect, useCallback, useRef } from "react";
import { AddVideo } from "./components/videos/addVideo";
import VideoTablePage from "./components/videos/page";
import type { VideoItem } from "./types";

function App() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setError] = useState<string | null>(null);

  const [processingStatus, setProcessingStatus] = useState<Record<string, string>>({});
  const wsRefs = useRef<Record<string, WebSocket>>({});

  const fetchVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/videos");
      const json = await res.json();
      if (!res.ok) {
        const detail =
          typeof json === "object" && "detail" in json
            ? (json.detail as string)
            : `Error ${res.status}`;
        throw new Error(detail);
      }
      const normalized: VideoItem[] = json.videos.map((raw: any) => ({
        _id: raw._id,
        id: raw._id.slice(-5),
        audio_object: raw.audio_object,
        created_at: new Date(raw.created_at)
          .toISOString()
          .replace("T", " ")
          .split(".")[0],
        emotion_prompt_result: raw.emotion_prompt_result,
        emotions: raw.emotions,
        transcript: raw.transcript,
        transcript_process_status: raw.transcript_process_status,
        video_filename: raw.video_filename,
        video_object: raw.video_object,
        extract_job_id: raw.extract_job_id,
      }));
      setVideos(normalized);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const listenToJob = useCallback(
    (videoId: string, jobId: string, initialLabel: string) => {
      setProcessingStatus((ps) => ({ ...ps, [videoId]: initialLabel }));
      const ws = new WebSocket(`ws://localhost:8000/ws/status/${jobId}`);
      wsRefs.current[jobId] = ws;

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data) as { status: string; meta: any };

        setProcessingStatus((ps) => ({ ...ps, [videoId]: initialLabel }));

        if (msg.status === "finished" || msg.status === "failed") {
          ws.close();
          setProcessingStatus((ps) => {
            const nxt = { ...ps };
            delete nxt[videoId];
            return nxt;
          });
          fetchVideos();
        }
      };

      ws.onerror = () => {
        ws.close();
        setProcessingStatus((ps) => {
          const nxt = { ...ps };
          delete nxt[videoId];
          return nxt;
        });
      };
    },
    [fetchVideos]
  );

  const handleUploadSuccess = useCallback(
    (videoId: string, extractJobId: string) => {
      listenToJob(videoId, extractJobId, "uploading");
      fetchVideos();
    },
    [listenToJob, fetchVideos]
  );

  const handleTranscribe = useCallback(
    async (videoId: string) => {
      const res = await fetch(
        `http://localhost:8000/videos/${videoId}/transcript`,
        { method: "POST" }
      );
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? `Error ${res.status}`);
      listenToJob(videoId, body.job_id, "transcribing");
    },
    [listenToJob]
  );

  const handleDelete = useCallback(
    async (rawId: string) => {
      try {
        const res = await fetch(`http://localhost:8000/videos/${rawId}`, {
          method: "DELETE",
        });
        if (res.status === 204) {
          await fetchVideos();
        } else {
          const json = await res.json().catch(() => ({}));
          throw new Error(json.detail ?? `Delete failed (${res.status})`);
        }
      } catch (err: any) {
        alert(`Could not delete video: ${err.message}`);
      }
    },
    [fetchVideos]
  );

  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach((ws) => ws.close());
    };
  }, []);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-xl w-full text-center space-y-6">
        <h1 className="text-2xl font-bold">Emotion Detection</h1>

        <AddVideo onUploadSuccess={(vidId, jobId) => handleUploadSuccess(vidId, jobId)} />

        <VideoTablePage
          loading={loading}
          error={errorMessage}
          data={videos}
          processingStatus={processingStatus}
          onDelete={handleDelete}
          onProcess={handleTranscribe}
        />
      </div>
    </div>
  );
}

export default App;
