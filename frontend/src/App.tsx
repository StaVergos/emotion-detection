import { useState, useEffect, useCallback } from "react";
import { AddVideo } from "./components/videos/addVideo";
import VideoTablePage from "./components/videos/page";
import type { VideoItem } from "./types";

function App() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setError] = useState<string | null>(null);

  const formatTimestamp = (iso: string) =>
    new Date(iso)
      .toISOString()
      .replace("T", " ")
      .split(".")[0];

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
        created_at: formatTimestamp(raw.created_at),
        emotion_prompt_result: raw.emotion_prompt_result,
        emotions: raw.emotions,
        transcript: raw.transcript,
        transcript_process_status: raw.transcript_process_status,
        video_filename: raw.video_filename,
        video_object: raw.video_object,
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

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`http://localhost:8000/videos/${id}`, {
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

  const handleProcess = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`http://localhost:8000/videos/${id}/process`, {
          method: "POST",
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `Process failed (${res.status})`);
        }
        if (res.status === 200)
          await fetchVideos();
      } catch (err: any) {
        alert(`Could not process transcript: ${err.message}`);
      }
    },
    [fetchVideos]
  );

  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-xl w-full text-center space-y-6">
        <h1 className="text-2xl font-bold">Emotion Detection Dashboard</h1>

        <AddVideo onUploadSuccess={fetchVideos} />

        <VideoTablePage
          loading={loading}
          error={errorMessage}
          data={videos}
          onDelete={handleDelete}
          onProcess={handleProcess}
        />
      </div>
    </div>
  );
}

export default App;
