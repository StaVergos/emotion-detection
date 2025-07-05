import { useState, useEffect, useCallback } from "react";
import { AddVideo } from "./components/videos/addVideo";
import VideoTablePage from "./components/videos/page";
import type { VideoItem, VideoItemRaw } from "./types";

function App() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setError] = useState<string | null>(null);

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

      const normalized: VideoItem[] = json.videos.map((raw: VideoItemRaw) => ({
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
        />
      </div>
    </div>
  );
}

export default App;
