import { useState, useEffect, useRef } from "react";
import VideoTablePage from "./components/videos/page";
import type { VideoColumn, VideoItem } from "./types";


function App() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-xl w-full text-center">
        <VideoTablePage />
      </div>
    </div>

  );
}

export default App;
