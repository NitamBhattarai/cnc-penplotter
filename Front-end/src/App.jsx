import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [gcodeText, setGcodeText] = useState('');
  const [textInput, setTextInput] = useState('');
  const [textPreview, setTextPreview] = useState('');

  // ========== File Upload / Drag & Drop ==========
  const handleFileChange = (e) => {
    const uploadedFiles = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...uploadedFiles]);

    if (uploadedFiles.length > 0) {
      const file = uploadedFiles[0];

      // Image preview
      if (file.type.startsWith('image/')) {
        setPreviewUrl(URL.createObjectURL(file));
        setTextPreview('');
      }

      // Text preview
      else if (file.type === 'text/plain') {
        setPreviewUrl(null);
        const reader = new FileReader();
        reader.onload = (e) => {
          setTextPreview(e.target.result);
        };
        reader.readAsText(file);
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  // ========== Backend / G-code ==========
  const handleSendToBackend = async () => {
    let content = '';

    // Priority: Typed text > Text file
    if (textInput.trim() !== '') {
      content = textInput;
    } else {
      const textFile = files.find(f => f.type === "text/plain");
      if (!textFile) return alert("Type something or upload a text file!");

      const reader = new FileReader();
      reader.onload = async (e) => {
        content = e.target.result;
        await sendToBackend(content);
      };
      reader.readAsText(textFile);
      return;
    }

    await sendToBackend(content);
  };

  const sendToBackend = async (content) => {
    try {
      const response = await axios.post(
        "https://cnc-penplotter.onrender.com/gcode",
        { text: content },
        { headers: { "Content-Type": "application/json" } }
      );
      setGcodeText(response.data);
    } catch (err) {
      console.error("Error:", err);
      alert("Failed to fetch G-code from backend.");
    }
  };

  // ========== Send to Plotter ==========
  const handleSendToPlotter = async () => {
    let content = '';

    if (textInput.trim() !== '') {
      content = textInput;
    } else {
      const textFile = files.find(f => f.type === "text/plain");
      if (!textFile) return alert("Type something or upload a text file!");

      const reader = new FileReader();
      reader.onload = async (e) => {
        content = e.target.result;
        await sendToPlotter(content);
      };
      reader.readAsText(textFile);
      return;
    }

    await sendToPlotter(content);
  };

  const sendToPlotter = async (content) => {
    try {
      await axios.post(
        "https://cnc-penplotter.onrender.com/submit",
        { text: content },
        { headers: { "Content-Type": "application/json" } }
      );
      alert("✅ Job queued for ESP32 plotter!");
    } catch (err) {
      console.error("Error:", err);
      alert("❌ Failed to queue job for plotter.");
    }
  };

  const downloadGcode = () => {
    if (!gcodeText) return alert("No G-code to download!");
    const blob = new Blob([gcodeText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "output.gcode";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <h1>Document Preview Studio</h1>
        <p>Upload text files or type text to generate G-code</p>
      </header>

      <main className="main-content">
        {/* Left Panel */}
        <section className="control-panel glass">

          {/* Typing Input */}
          <div className="typing-input">
            <label htmlFor="typingText">Type Your Text:</label>
            <textarea
              id="typingText"
              value={textInput}
              onChange={(e) => {
                setTextInput(e.target.value);
                setTextPreview(e.target.value);
              }}
              placeholder="Enter text here..."
              rows={5}
            />
          </div>

          {/* Upload Area */}
          <div
            className="upload-area glass"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <div className="upload-content">
              <div className="upload-icon">☁️</div>
              <h3>Drag & Drop Files Here</h3>
              <p>or click browse</p>
              <label className="browse-btn">
                Browse Files
                <input
                  type="file"
                  multiple
                  accept=".txt,image/jpeg,image/png,image/gif"
                  onChange={handleFileChange}
                  hidden
                />
              </label>
              <p className="support-text">
                Supports: Text (.txt), images (.jpg, .png, .gif)
              </p>
            </div>
          </div>

          {/* Uploaded Files */}
          <div className="uploaded-files">
            <h4>Uploaded Files</h4>
            {files.length === 0 ? (
              <p>No files uploaded yet</p>
            ) : (
              <ul>
                {files.map((file, i) => (
                  <li key={i}>
                    {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button className="download-btn" onClick={handleSendToBackend}>
              ⬇️ Generate G-code
            </button>
            <button className="download-btn" onClick={downloadGcode}>
              💾 Download G-code
            </button>
            <button className="download-btn" onClick={handleSendToPlotter}>
              🖊️ Send to Plotter
            </button>
          </div>
        </section>

        {/* Right Panel */}
        <section className="preview-panel glass">
          <div className="preview-area">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="Preview"
                className="preview-image"
              />
            ) : textPreview ? (
              <div className="text-preview">
                <pre>{textPreview}</pre>
              </div>
            ) : (
              <div className="empty-preview">
                <div className="icon">📄</div>
                <h4>No content to preview</h4>
                <p>Type text or upload a file to see the preview here</p>
              </div>
            )}
          </div>

          {/* G-code Preview */}
          {gcodeText && (
            <div className="preview-gcode">
              <h4>G-code Preview</h4>
              <pre>{gcodeText}</pre>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
